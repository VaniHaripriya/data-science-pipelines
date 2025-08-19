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
        
        # Handle experiment object attributes (same pattern as create_test_pipelines.py)
        experiment_id = getattr(experiment, 'experiment_id', None) or getattr(experiment, 'id', None)           
        
        # Get pipeline details from KFP API to create a run
        print(f"🔍 Making API request to: {self.api_base}/pipelines")
        pipeline_response = requests.get(
            f"{self.api_base}/pipelines",
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 Pipeline API response status: {pipeline_response.status_code}")
        if pipeline_response.status_code != 200:
            print(f"❌ Pipeline API response text: {pipeline_response.text}")
            
            # Try to test basic API connectivity
            print("🔍 Testing basic API connectivity...")
            try:
                health_response = requests.get(f"{KFP_ENDPOINT}/apis/v2beta1/healthz")
                print(f"Health check status: {health_response.status_code}")
                print(f"Health check response: {health_response.text}")
            except Exception as e:
                print(f"Health check failed: {e}")
        
        if pipeline_response.status_code == 200:
            pipelines = pipeline_response.json().get("pipelines", [])
            target_pipeline = None
            
            # Find the pipeline by name
            for pipeline in pipelines:
                if pipeline["name"] == first_pipeline_name:
                    target_pipeline = pipeline
                    break
            
            if target_pipeline:
                # Get pipeline versions for this pipeline
                version_response = requests.get(
                    f"{self.api_base}/pipelines/{target_pipeline['id']}/versions",
                    headers={"Content-Type": "application/json"}
                )
                
                if version_response.status_code == 200:
                    versions = version_response.json().get("versions", [])
                    if versions:
                        target_version = versions[0]  # Use first available version
                        
                        # Create a run using the KFP client
                        run_data = client.run_pipeline(
                            experiment_id=experiment_id,
                            job_name="k8s-execution-test-run",
                            pipeline_id=target_pipeline['id'],
                            version_id=target_version['id'],
                            params={}  # No parameters for this test
                        )
                        
                        # Get run ID using the appropriate attribute
                        run_id = getattr(run_data, 'run_id', None) or getattr(run_data, 'id', None)
                        run_name = getattr(run_data, 'display_name', None) or getattr(run_data, 'name', None) or "k8s-execution-test-run"
                        
                        print(f"✅ Successfully created and started run: {run_name} (ID: {run_id})")
                        
                        # Verify run was created
                        self.assertIsNotNone(run_id, "Run should have an ID")
                        
                        # Wait a moment and check run status
                        time.sleep(5)
                        
                        # Get run details to verify execution with explicit status code check
                        run_details_response = requests.get(
                            f"{self.api_base}/runs/{run_id}",
                            headers={"Content-Type": "application/json"}
                        )
                        
                        # Explicitly check for 200 status code
                        print(f"📊 Run details API response status: {run_details_response.status_code}")
                        self.assertEqual(run_details_response.status_code, 200, "Run details API should return status code 200")
                        
                        run_details = run_details_response.json()
                        run_status = run_details.get("status", "UNKNOWN")
                        print(f"✅ Run status: {run_status}")
                        print(f"✅ Successfully executed migrated pipeline in K8s mode with 200 status")
                        
                        # Verify run details structure
                        self.assertIn("id", run_details, "Run should have an ID")
                        self.assertIn("name", run_details, "Run should have a name")
                        self.assertIn("status", run_details, "Run should have a status")
                        
                        print("✅ Run details match expected structure")
                        
                    else:
                        self.fail("No pipeline versions available for execution test")
                else:
                    self.fail(f"Failed to get pipeline versions: {version_response.status_code}")
            else:
                self.fail(f"Pipeline {first_pipeline_name} not found in KFP API")
        else:
            self.fail(f"Failed to get pipelines from KFP API: {pipeline_response.status_code}")

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
           
            duplicate_pipeline_data = {
                "apiVersion": "pipelines.kubeflow.org/v2beta1",
                "kind": "Pipeline",
                "metadata": {
                    "name": existing_pipeline_name,
                    "namespace": "kubeflow"
                },
                "spec": {
                    "displayName": existing_pipeline_name
                }
            }
            
            response = requests.post(
                f"{self.api_base}/pipelines",
                json=duplicate_pipeline_data,
                headers={"Content-Type": "application/json"}
            )            
           
            self.assertEqual(response.status_code, 409, 
                f"Expected 409 conflict error when creating duplicate pipeline, but got {response.status_code}: {response.text}")       
           
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
        
        # Get available pipelines
        pipeline_response = requests.get(
            f"{self.api_base}/pipelines",
            headers={"Content-Type": "application/json"}
        )
        
        if pipeline_response.status_code == 200:
            pipelines = pipeline_response.json().get("pipelines", [])
            if pipelines:
                pipeline = pipelines[0]
                pipeline_id = pipeline["id"]
                
                # Get pipeline versions  
                version_response = requests.get(
                    f"{self.api_base}/pipelines/{pipeline_id}/versions",
                    headers={"Content-Type": "application/json"}
                )
                
                if version_response.status_code == 200:
                    versions = version_response.json().get("versions", [])
                    if versions:
                        version = versions[0]
                        version_id = version["id"]                       
                        
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
                        self.fail("No pipeline versions available for run creation")
                else:
                    self.fail(f"Failed to get pipeline versions: {version_response.status_code} - {version_response.text}")
            else:
                self.fail("No pipelines available for run creation")
        else:
            self.fail(f"Failed to get pipelines: {pipeline_response.status_code} - {pipeline_response.text}")

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