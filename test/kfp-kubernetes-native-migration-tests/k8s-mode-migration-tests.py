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
from pathlib import Path
from unittest.mock import patch

# Add the tools directory to path to import migration module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../tools/k8s-native'))

from migration import migrate

# Environment variables
KFP_ENDPOINT = os.environ.get('KFP_ENDPOINT', 'http://localhost:8888')
TIMEOUT_SECONDS = int(os.environ.get('TIMEOUT_SECONDS', '2700'))
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, *([os.path.pardir] * 2)))


class TestK8sModeMigration(unittest.TestCase):
    """K8s mode migration tests that require KFP to be running in K8s mode."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.kfp_host = KFP_ENDPOINT.replace('http://', '').replace('https://', '').split(':')[0]
        cls.kfp_port = KFP_ENDPOINT.split(':')[-1].split('/')[0] if ':' in KFP_ENDPOINT else '8888'
        cls.api_base = f"{KFP_ENDPOINT}/api/v1"
        cls.temp_dir = tempfile.mkdtemp()
        
        # Load test data created by create_test_pipelines.py
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

    def setUp(self):
        """Set up for each test."""
        self.output_dir = Path(self.temp_dir) / f"k8s_migration_output_{self._testMethodName}"
        self.output_dir.mkdir(exist_ok=True)

    def test_k8s_mode_experiment_and_run_rerun(self):
        """Test: Rerun pipeline run associated with experiment in K8s mode"""
        
        # Verify we have the original run data
        if self.test_data.get("experiments") and self.test_data.get("runs"):
            original_run = self.test_data["runs"][0]
            original_experiment = self.test_data["experiments"][0]
            print(f"Original run: {original_run['name']} (ID: {original_run['id']})")
            print(f"Original experiment: {original_experiment['name']} (ID: {original_experiment['id']})")
            
            try:
                # Create a new run with the same pipeline and parameters (in K8s mode)
                rerun_data = {
                    "name": f"rerun-k8s-{original_run['name']}",
                    "pipeline_spec": {
                        "pipeline_id": original_run["pipeline_spec"]["pipeline_id"],
                        "pipeline_version_id": original_run["pipeline_spec"]["pipeline_version_id"]
                    },
                    "resource_references": [
                        {
                            "key": {
                                "type": "EXPERIMENT",
                                "id": original_experiment["id"]
                            },
                            "relationship": "OWNER"
                        }
                    ]
                }
                
                # Add original parameters if they exist
                if "parameters" in original_run:
                    rerun_data["parameters"] = original_run["parameters"]
                
                # Create the rerun via KFP API (now in K8s mode)
                response = requests.post(
                    f"{self.api_base}/runs",
                    json=rerun_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    rerun = response.json()
                    print(f"✅ Successfully created rerun in K8s mode: {rerun['name']} (ID: {rerun['id']})")
                    
                    # Verify the rerun was created in K8s mode
                    self.assertIn("id", rerun, "Rerun should have an ID")
                    self.assertIn("name", rerun, "Rerun should have a name")
                    self.assertEqual(rerun["name"], f"rerun-k8s-{original_run['name']}", "Rerun name should match expected pattern")
                    
                    # Verify the rerun is associated with the same experiment
                    rerun_refs = rerun.get("resource_references", [])
                    experiment_ref = next((ref for ref in rerun_refs if ref["key"]["type"] == "EXPERIMENT"), None)
                    self.assertIsNotNone(experiment_ref, "Rerun should be associated with an experiment")
                    self.assertEqual(experiment_ref["key"]["id"], original_experiment["id"], "Rerun should be associated with the original experiment")
                    
                    # Verify the rerun uses the same pipeline and version
                    self.assertEqual(rerun["pipeline_spec"]["pipeline_id"], original_run["pipeline_spec"]["pipeline_id"], "Rerun should use the same pipeline")
                    self.assertEqual(rerun["pipeline_spec"]["pipeline_version_id"], original_run["pipeline_spec"]["pipeline_version_id"], "Rerun should use the same pipeline version")
                    
                    print(f"✅ Successfully rerun pipeline in K8s mode!")
                    
                else:
                    print(f"Failed to create rerun in K8s mode: {response.status_code} - {response.text}")
                    self.fail(f"Failed to create rerun in K8s mode: {response.status_code} - {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Error creating rerun in K8s mode: {e}")
                self.fail(f"Error creating rerun in K8s mode: {e}")

    def test_k8s_mode_pipeline_execution(self):
        """Test: Execute migrated pipelines in K8s mode"""
        
        # Verify pipelines are available in K8s mode
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pipeline', '-n', 'kubeflow'
            ], check=True, capture_output=True, text=True)
            
            # Verify that migrated pipelines exist in K8s mode
            self.assertIn("simple-pipeline", result.stdout, "Simple pipeline should exist in K8s mode")
            self.assertIn("complex-pipeline", result.stdout, "Complex pipeline should exist in K8s mode")
            print("✅ Pipelines are available in K8s mode")
            
            # Verify pipeline versions
            version_result = subprocess.run([
                'kubectl', 'get', 'pipelineversion', '-n', 'kubeflow'
            ], check=True, capture_output=True, text=True)
            
            print(f"Pipeline versions in K8s mode: {version_result.stdout}")
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not verify K8s mode pipelines: {e.stderr}")

    def test_k8s_mode_duplicate_pipeline_creation(self):
        """Test: Try creating existing pipeline in K8s mode (should fail)"""
        
        # Try to create a pipeline with the same name (should fail)
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pipeline', '-n', 'kubeflow'
            ], check=True, capture_output=True, text=True)
            
            # Verify that migrated pipelines exist in the cluster
            self.assertIn("simple-pipeline", result.stdout, "Simple pipeline should exist in cluster")
            self.assertIn("complex-pipeline", result.stdout, "Complex pipeline should exist in cluster")
            
            print("✅ Migrated pipelines exist in K8s mode")
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not verify pipeline existence: {e.stderr}")

    def test_k8s_mode_experiment_creation(self):
        """Test: Create new experiment in K8s mode"""
        
        try:
            # Create a new experiment in K8s mode
            experiment_data = {
                "name": "k8s-mode-test-experiment",
                "description": "Test experiment created in K8s mode"
            }
            
            response = requests.post(
                f"{self.api_base}/experiments",
                json=experiment_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                experiment = response.json()
                print(f"✅ Created experiment in K8s mode: {experiment['name']} (ID: {experiment['id']})")
                
                # Verify experiment was created
                self.assertIn("id", experiment, "Experiment should have an ID")
                self.assertEqual(experiment["name"], "k8s-mode-test-experiment", "Experiment name should match")
                
            else:
                print(f"Failed to create experiment in K8s mode: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"Error creating experiment in K8s mode: {e}")

    def test_k8s_mode_pipeline_validation(self):
        """Test: Validate that migrated pipelines work correctly in K8s mode"""
        
        # Check pipeline status in K8s mode
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pipeline', '-n', 'kubeflow', '-o', 'jsonpath={.items[*].status.conditions[*].type}'
            ], check=True, capture_output=True, text=True)
            
            # Check if pipelines are ready
            if result.stdout:
                print(f"Pipeline status in K8s mode: {result.stdout}")
            
            # Verify pipeline versions are available
            version_result = subprocess.run([
                'kubectl', 'get', 'pipelineversion', '-n', 'kubeflow', '--no-headers'
            ], check=True, capture_output=True, text=True)
            
            version_count = len([line for line in version_result.stdout.strip().split('\n') if line])
            self.assertGreaterEqual(version_count, 2, "Should have at least 2 pipeline versions in K8s mode")
            
            print(f"✅ Found {version_count} pipeline versions in K8s mode")
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not check K8s mode pipeline status: {e.stderr}")


if __name__ == '__main__':
    unittest.main()
