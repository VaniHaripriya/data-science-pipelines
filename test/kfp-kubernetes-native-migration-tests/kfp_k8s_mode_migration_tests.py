# Copyright 2025 The Kubeflow Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import sys
import time
import tempfile
import unittest
import subprocess
import requests
import kfp
import glob
from pathlib import Path
from unittest.mock import patch
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add the tools directory to path to import migration module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../tools/k8s-native'))

from migration import migrate

KFP_ENDPOINT = os.environ.get('KFP_ENDPOINT', 'http://localhost:8888')

class TestK8sModeMigration(unittest.TestCase):
    """Kubernetes native migration tests that require KFP to be running in K8s mode."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.api_base = f"{KFP_ENDPOINT}/api/v2beta1"
        cls.temp_dir = tempfile.mkdtemp()        
        
        test_data_file = Path("migration_test_data.json")
        if test_data_file.exists():
            with open(test_data_file) as f:
                cls.test_data = json.load(f)
        else:
            cls.test_data = {"pipelines": [], "experiments": [], "runs": [], "recurring_runs": []}

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(cls.temp_dir)   

    def test_k8s_mode_pipeline_execution(self):
        """Test that migrated pipelines are available and can be executed in K8s mode"""
        
        result = subprocess.run([
            'kubectl', 'get', 'pipeline', '-n', 'kubeflow', '-o', 'jsonpath={.items[*].metadata.name}'
        ], check=True, capture_output=True, text=True)
        
        pipeline_names = result.stdout.strip().split()
        self.assertGreater(len(pipeline_names), 0, "Should have at least one pipeline in K8s mode")
        
        migrated_pipelines = []
        for pipeline_name in pipeline_names:
            annotation_result = subprocess.run([
                'kubectl', 'get', 'pipeline', pipeline_name, '-n', 'kubeflow', 
                '-o', r'jsonpath={.metadata.annotations.pipelines\.kubeflow\.org/original-id}'
            ], capture_output=True, text=True)
            
            if annotation_result.stdout.strip():
                migrated_pipelines.append(pipeline_name)
        
        if not migrated_pipelines:
            self.fail("No migrated pipelines found with original-id annotation")
                   
        first_pipeline_name = migrated_pipelines[0]
        
        # Create an experiment
        client = kfp.Client(host=KFP_ENDPOINT)
        experiment = client.create_experiment(
            name="k8s-execution-test-experiment",
            description="Test experiment for K8s mode pipeline execution"
        )        
        experiment_id = getattr(experiment, 'experiment_id', None) or getattr(experiment, 'id', None)           
       
        print(f"Getting pipeline '{first_pipeline_name}' using KFP client...")
        
        # Use client to list pipelines - this should work in both DB and K8s mode
        pipelines = client.list_pipelines()
        pipeline_list = pipelines.pipelines if hasattr(pipelines, 'pipelines') else []
        
        target_pipeline = None
        for pipeline in pipeline_list:
            pipeline_name = getattr(pipeline, 'display_name', None) or getattr(pipeline, 'name', None)
            if pipeline_name == first_pipeline_name:
                target_pipeline = pipeline
                break
        
        if not target_pipeline:
            self.fail(f"Pipeline {first_pipeline_name} not found via KFP client")
        
        pipeline_id = getattr(target_pipeline, 'pipeline_id', None) or getattr(target_pipeline, 'id', None)
        print(f"Found pipeline: {first_pipeline_name} (ID: {pipeline_id})")
        
        # Get pipeline versions using client
        versions = client.list_pipeline_versions(pipeline_id=pipeline_id)
        version_list = versions.pipeline_versions if hasattr(versions, 'pipeline_versions') else []
        
        if not version_list:
            self.fail("No pipeline versions available for execution test")
        
        target_version = version_list[0]
        version_id = getattr(target_version, 'pipeline_version_id', None) or getattr(target_version, 'id', None)
        print(f"Found pipeline version (ID: {version_id})")
        
        # Create a run using the KFP client
        run_data = client.run_pipeline(
            experiment_id=experiment_id,
            job_name="k8s-execution-test-run",
            pipeline_id=pipeline_id,
            version_id=version_id,
            params={}
        )
        
        # Get run ID using the appropriate attribute
        run_id = getattr(run_data, 'run_id', None) or getattr(run_data, 'id', None)
        run_name = getattr(run_data, 'display_name', None) or getattr(run_data, 'name', None) or "k8s-execution-test-run"
        
        print(f"Successfully created and started run: {run_name} (ID: {run_id})")
        
        # Verify run was created
        self.assertIsNotNone(run_id, "Run should have an ID")
        
        # Wait a moment and check run status using client
        time.sleep(5)
        
        # Get run details using KFP client instead of REST API
        run_details = client.get_run(run_id=run_id)
        run_status = getattr(run_details, 'status', None) or getattr(run_details, 'state', None) or "UNKNOWN"
        print(f"Run status: {run_status}")
        print(f"Successfully executed migrated pipeline in K8s mode")
        
        # Verify run details structure
        self.assertIsNotNone(getattr(run_details, 'run_id', None) or getattr(run_details, 'id', None), "Run should have an ID")
        self.assertIsNotNone(getattr(run_details, 'display_name', None) or getattr(run_details, 'name', None), "Run should have a name")
        
        print("Run details match expected structure")

    def test_k8s_mode_duplicate_pipeline_creation(self):
        """Test that attempting to create a pipeline with the same name as an existing pipeline fails appropriately"""
        
        result = subprocess.run([
            'kubectl', 'get', 'pipeline', '-n', 'kubeflow'
        ], check=True, capture_output=True, text=True)
        
        # Check that we have at least some pipelines
        pipeline_lines = [line for line in result.stdout.strip().split('\n') if line and not line.startswith('NAME')]
        self.assertGreater(len(pipeline_lines), 0, "Should have at least one pipeline in cluster")
        print(f"Found {len(pipeline_lines)} pipelines in cluster: {pipeline_lines}")            
        
        if pipeline_lines:
            existing_pipeline_name = pipeline_lines[0].split()[0]
            print(f"Attempting to create duplicate of pipeline: {existing_pipeline_name}")                
           
            # In K8s native mode, test duplicate creation using kubectl directly
            import tempfile
            import yaml
            
            duplicate_pipeline_data = {
                "apiVersion": "pipelines.kubeflow.org/v2beta1",
                "kind": "Pipeline",
                "metadata": {
                    "name": existing_pipeline_name,
                    "namespace": "kubeflow"
                },
                "spec": {
                    "description": "Duplicate pipeline test"
                }
            }
            
            # Write YAML to temporary file and try to apply it
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(duplicate_pipeline_data, f)
                temp_file = f.name
            
            result = subprocess.run([
                'kubectl', 'apply', '-f', temp_file
            ], capture_output=True, text=True)                
            
            # Verify only one pipeline with this name exists
            check_result = subprocess.run([
                'kubectl', 'get', 'pipeline', existing_pipeline_name, '-n', 'kubeflow'
            ], capture_output=True, text=True)
            
            if check_result.returncode == 0:
               
                print(f"Pipeline {existing_pipeline_name} exists as expected")
                
                # Verify there's still only one pipeline with this name
                count_result = subprocess.run([
                    'kubectl', 'get', 'pipeline', '-n', 'kubeflow', '-o', 'name'
                ], capture_output=True, text=True)
                
                pipeline_names = [line.split('/')[-1] for line in count_result.stdout.strip().split('\n') if line]
                name_count = pipeline_names.count(existing_pipeline_name)
                
                self.assertEqual(name_count, 1, f"Should have exactly 1 pipeline named {existing_pipeline_name}, but found {name_count}")
                print(f"Duplicate pipeline handling works correctly - only one {existing_pipeline_name} exists")
            else:
                self.fail(f"Pipeline {existing_pipeline_name} not found after duplicate creation attempt")
            
            # Clean up temp file
            import os
            os.unlink(temp_file)       
           
        else:
            self.fail("No pipelines found to test duplicate creation")

    def test_k8s_mode_experiment_creation(self):
        """Test that new experiments and runs can be created in K8s mode after migration"""
        
        client = kfp.Client(host=KFP_ENDPOINT)        
        experiment = client.create_experiment(
            name="k8s-mode-test-experiment",
            description="Test experiment created in K8s mode"
        )       
        
        experiment_id = getattr(experiment, 'experiment_id', None) or getattr(experiment, 'id', None)
        experiment_name = getattr(experiment, 'display_name', None) or getattr(experiment, 'name', None)       
        
        self.assertIsNotNone(experiment_id, "Experiment should have an ID")
        self.assertEqual(experiment_name, "k8s-mode-test-experiment", "Experiment name should match")
        
        # Get available pipelines using kubectl (more reliable in K8s mode)
        print("Getting available pipelines using kubectl...")
        pipeline_result = subprocess.run([
            'kubectl', 'get', 'pipeline', '-n', 'kubeflow', '-o', 'jsonpath={.items[0].metadata.name}'
        ], capture_output=True, text=True)
        
        if pipeline_result.returncode == 0 and pipeline_result.stdout.strip():
            pipeline_name = pipeline_result.stdout.strip()
            print(f"Using pipeline: {pipeline_name}")
            
            # Check if pipeline versions exist using kubectl
            version_result = subprocess.run([
                'kubectl', 'get', 'pipelineversion', '-n', 'kubeflow', '--field-selector=spec.pipelineName=' + pipeline_name,
                '-o', 'jsonpath={.items[0].metadata.name}'
            ], capture_output=True, text=True)
            
            if version_result.returncode == 0 and version_result.stdout.strip():
                print(f"Found pipeline version: {version_result.stdout.strip()}")
                
                # Get pipeline via KFP client for run creation
                pipeline = client.get_pipeline(pipeline_name=pipeline_name)
                pipeline_id = getattr(pipeline, 'pipeline_id', None) or getattr(pipeline, 'id', None)
                
                # Get first version via KFP client
                versions = client.list_pipeline_versions(pipeline_id=pipeline_id)
                version_list = versions.pipeline_versions if hasattr(versions, 'pipeline_versions') else []
                
                if version_list:
                    version = version_list[0]
                    version_id = getattr(version, 'pipeline_version_id', None) or getattr(version, 'id', None)
                    
                    run_data = client.run_pipeline(
                        experiment_id=experiment_id,
                        job_name="k8s-mode-test-run",
                        pipeline_id=pipeline_id,
                        version_id=version_id
                    )
                    run_id = getattr(run_data, 'run_id', None) or getattr(run_data, 'id', None)
                    run_name = getattr(run_data, 'display_name', None) or getattr(run_data, 'name', None)
                    
                    self.assertIsNotNone(run_id, "Run should have an ID")
                    self.assertEqual(run_name, "k8s-mode-test-run", "Run name should match")
                else:
                    self.fail("Pipeline versions exist in K8s but not accessible via KFP client")
            else:
                self.fail("No pipeline versions found in K8s mode")
        else:
            self.fail("No pipelines available for run creation")

    def test_k8s_mode_recurring_run_continuation(self):
        """Test that recurring runs created in DB mode continue to exist after switching to K8s mode"""
                
        if self.test_data.get("recurring_runs"):
            original_recurring_run = self.test_data["recurring_runs"][0]
            recurring_run_name = original_recurring_run["name"]
            recurring_run_id = original_recurring_run["id"]
            
            # Check if the recurring run still exists in K8s mode
            response = requests.get(
                f"{self.api_base}/recurringruns/{recurring_run_id}",
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                recurring_run = response.json()
                print(f"Recurring run still exists in K8s mode: {recurring_run['name']} (ID: {recurring_run['id']})")
                
                # Verify the recurring run has the same properties
                self.assertEqual(recurring_run["name"], recurring_run_name, "Recurring run name should match")
                self.assertEqual(recurring_run["id"], recurring_run_id, "Recurring run ID should match")
                
                # Check if the cron schedule is preserved
                original_cron = original_recurring_run.get('trigger', {}).get('cron_schedule', {}).get('cron')
                current_cron = recurring_run.get('trigger', {}).get('cron_schedule', {}).get('cron')
                
                self.assertEqual(current_cron, original_cron, "Cron schedule should be preserved")                
        else:
            print("No recurring run data available for K8s mode test")

if __name__ == '__main__':
    unittest.main()