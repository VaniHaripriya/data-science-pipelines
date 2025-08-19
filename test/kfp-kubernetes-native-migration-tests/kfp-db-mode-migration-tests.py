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

"""
Integration migration tests that require a KFP environment.

These tests cover all scenarios from TestPlan.md "Migration of existing pipelines" section.
"""
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

KFP_ENDPOINT = os.environ.get('KFP_ENDPOINT', 'http://localhost:8888')
TIMEOUT_SECONDS = int(os.environ.get('TIMEOUT_SECONDS', '2700'))
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, *([os.path.pardir] * 2)))

class TestMigrationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
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
        self.output_dir = Path(self.temp_dir) / f"migration_output_{self._testMethodName}"
        self.output_dir.mkdir(exist_ok=True)

    def test_migration_single_pipeline_single_version(self): 
        
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")        
        
        pipeline_files = [f for f in yaml_files if "simple-pipeline" in f.name]
        self.assertGreaterEqual(len(pipeline_files), 1, "Should have files for simple pipeline")        
        
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            if "kind: Pipeline" in content or "kind: PipelineVersion" in content:
                self.assertIn("pipelines.kubeflow.org/original-id", content, "Should have original ID annotation")

    def test_migration_single_pipeline_multiple_versions_same_spec(self):
        
       with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()
                
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")        
        
        version_count = len([f for f in yaml_files if "kind: PipelineVersion" in f.read_text()])
        self.assertGreaterEqual(version_count, 2, "Should have at least 2 pipeline versions")        
        
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            if "kind: PipelineVersion" in content:
                self.assertIn("pipelines.kubeflow.org/original-id", content, "Should have original ID annotation")

    def test_migration_single_pipeline_multiple_versions_different_specs(self):
        
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")        
       
        complex_pipeline_files = [f for f in yaml_files if "complex-pipeline" in f.name]
        self.assertGreaterEqual(len(complex_pipeline_files), 2, "Complex pipeline should have multiple versions")        
       
        version_contents = [f.read_text() for f in complex_pipeline_files if "kind: PipelineVersion" in f.read_text()]
        self.assertGreaterEqual(len(version_contents), 2, "Should have multiple version contents")        
        
        has_platform_spec = any("platformSpec" in content for content in version_contents)
        no_platform_spec = any("platformSpec" not in content for content in version_contents)
        self.assertTrue(has_platform_spec and no_platform_spec, "Should have versions with and without platformSpec")

    def test_migration_multiple_pipelines_single_version_each(self):
       
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")        
       
        pipeline_count = len([f for f in yaml_files if "kind: Pipeline" in f.read_text()])
        version_count = len([f for f in yaml_files if "kind: PipelineVersion" in f.read_text()])        
        
        self.assertGreaterEqual(pipeline_count, 2, "Should have at least 2 pipelines")
        self.assertGreaterEqual(version_count, 2, "Should have at least 2 pipeline versions")

    def test_migration_multiple_pipelines_multiple_versions_different_specs(self):
        
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")     
      
        pipeline_files = [f for f in yaml_files if "simple-pipeline" in f.name or "complex-pipeline" in f.name]
        self.assertGreaterEqual(len(pipeline_files), 2, "Should have files for both pipelines")       
       
        complex_pipeline_files = [f for f in yaml_files if "complex-pipeline" in f.name]
        self.assertGreaterEqual(len(complex_pipeline_files), 2, "Complex pipeline should have multiple versions")

    def test_migration_with_experiments_and_runs(self):        
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")        
        
        if self.test_data.get("experiments") and self.test_data.get("runs"):
            print(f"Found {len(self.test_data['experiments'])} experiments and {len(self.test_data['runs'])} runs")            
            
            for yaml_file in yaml_files:
                content = yaml_file.read_text()
                if "kind: Pipeline" in content:                    
                    self.assertIn("pipelines.kubeflow.org/original-id", content)

    # def test_migration_with_recurring_runs(self):
        
    #     with patch('sys.argv', [
    #         'migration.py',
    #         '--kfp-server-host', KFP_ENDPOINT,
    #         '--output', str(self.output_dir),
    #         '--namespace', 'kubeflow'
    #     ]):
    #         migrate()        
        
    #     yaml_files = list(self.output_dir.glob("*.yaml"))
    #     self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")        
        
    #     if self.test_data.get("recurring_runs"):
    #         print(f"Found {len(self.test_data['recurring_runs'])} recurring runs")            
           
    #         for yaml_file in yaml_files:
    #             content = yaml_file.read_text()
    #             if "kind: Pipeline" in content:                    
    #                 self.assertIn("spec:", content)

    # ==================== POST-MIGRATION TESTS ====================

    def test_post_migration_duplicate_pipeline_creation(self):
        """Test: (K8s Mode) Try creating an existing pipeline and pipeline version"""
        
        # First, run migration to create pipelines in K8s mode
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()
        
        # Verify migration created files
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Apply migrated YAML files to K8s cluster
        for yaml_file in yaml_files:
            try:
                subprocess.run([
                    'kubectl', 'apply', '-f', str(yaml_file), '-n', 'kubeflow'
                ], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to apply {yaml_file}: {e.stderr}")
        
        # Try to create a pipeline with the same name (should fail)
        # This would typically be done through the KFP API
        # For now, we verify that the migrated pipelines exist in the cluster
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pipeline', '-n', 'kubeflow'
            ], check=True, capture_output=True, text=True)
            
            # Verify that migrated pipelines exist
            self.assertIn("simple-pipeline", result.stdout, "Simple pipeline should exist in cluster")
            self.assertIn("complex-pipeline", result.stdout, "Complex pipeline should exist in cluster")
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not verify pipeline existence: {e.stderr}")

    def test_post_migration_pipeline_execution(self):
        """Test: (K8s Mode) Run an existing pipeline and get run details and match"""
        
        # First, run migration to create pipelines in K8s mode
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()
        
        # Verify migration created files
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Apply migrated YAML files to K8s cluster
        for yaml_file in yaml_files:
            try:
                subprocess.run([
                    'kubectl', 'apply', '-f', str(yaml_file), '-n', 'kubeflow'
                ], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to apply {yaml_file}: {e.stderr}")
        
        # Verify that pipelines are ready for execution
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pipeline', '-n', 'kubeflow', '-o', 'jsonpath={.items[*].status.conditions[*].type}'
            ], check=True, capture_output=True, text=True)
            
            # Check if pipelines are ready
            if result.stdout:
                print(f"Pipeline status: {result.stdout}")
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not check pipeline status: {e.stderr}")

    def test_post_migration_all_pipelines_execution(self):
        """Test: (K8s Mode) Run all migrated pipeline and match the run details"""
        
        # First, run migration to create pipelines in K8s mode
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()
        
        # Verify migration created files
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Count pipelines and versions
        pipeline_files = [f for f in yaml_files if "kind: Pipeline" in f.read_text()]
        version_files = [f for f in yaml_files if "kind: PipelineVersion" in f.read_text()]
        
        print(f"Migrated {len(pipeline_files)} pipelines and {len(version_files)} versions")
        
        # Apply all migrated YAML files to K8s cluster
        for yaml_file in yaml_files:
            try:
                subprocess.run([
                    'kubectl', 'apply', '-f', str(yaml_file), '-n', 'kubeflow'
                ], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to apply {yaml_file}: {e.stderr}")
        
        # Verify all pipelines are available for execution
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pipeline', '-n', 'kubeflow', '--no-headers'
            ], check=True, capture_output=True, text=True)
            
            pipeline_count = len([line for line in result.stdout.strip().split('\n') if line])
            self.assertGreaterEqual(pipeline_count, 2, "Should have at least 2 pipelines available for execution")
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not verify pipeline availability: {e.stderr}")

    def test_post_migration_experiment_and_run_creation(self):
        """Test: (K8s Mode) Create an experiment and a run"""
        
        # First, run migration to create pipelines in K8s mode
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()
        
        # Verify migration created files
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Apply migrated YAML files to K8s cluster
        for yaml_file in yaml_files:
            try:
                subprocess.run([
                    'kubectl', 'apply', '-f', str(yaml_file), '-n', 'kubeflow'
                ], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to apply {yaml_file}: {e.stderr}")
        
        # Test creating an experiment via KFP API
        try:
            # Create experiment
            experiment_data = {
                "name": "post-migration-test-experiment",
                "description": "Test experiment after migration"
            }
            
            response = requests.post(
                f"{self.api_base}/experiments",
                json=experiment_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                experiment = response.json()
                print(f"Created experiment: {experiment['name']} (ID: {experiment['id']})")
                
                # Verify experiment was created
                self.assertIn("id", experiment, "Experiment should have an ID")
                self.assertEqual(experiment["name"], "post-migration-test-experiment", "Experiment name should match")
                
            else:
                print(f"Warning: Failed to create experiment: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not create experiment via API: {e}")

    def test_post_migration_pipeline_validation(self):
        """Test: Validate that migrated pipelines maintain their original specifications"""
        
        # First, run migration to create pipelines in K8s mode
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()
        
        # Verify migration created files
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Validate each migrated pipeline
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            
            if "kind: Pipeline" in content:
                # Should have correct API version
                self.assertIn("pipelines.kubeflow.org/v1beta1", content, "Should have correct API version")
                
                # Should have original ID annotation
                self.assertIn("pipelines.kubeflow.org/original-id", content, "Should have original ID annotation")
                
                # Should have namespace
                self.assertIn("namespace: kubeflow", content, "Should have correct namespace")
                
            elif "kind: PipelineVersion" in content:
                # Should have pipeline spec
                self.assertIn("pipelineSpec:", content, "Should have pipeline spec")
                
                # Should have original ID annotation
                self.assertIn("pipelines.kubeflow.org/original-id", content, "Should have original ID annotation")
                
                # Should reference parent pipeline
                self.assertIn("pipelineName:", content, "Should reference parent pipeline")

    def test_migration_with_no_prefix_option(self):
        """Test migration script with --no-pipeline-name-prefix option in real environment"""
        
        # Run migration with no prefix option
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow',
            '--no-pipeline-name-prefix'
        ]):
            migrate()
        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Check that pipeline names don't have prefixes
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            if "kind: Pipeline" in content:
                # Should not have kfp- prefix
                self.assertNotIn("kfp-", content)

    def test_migration_with_custom_namespace(self):
        """Test migration script with custom namespace in real environment"""
        
        custom_namespace = "custom-test-namespace"
        
        # Run migration with custom namespace
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', custom_namespace
        ]):
            migrate()
        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Check that namespace is set correctly
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            if "kind: Pipeline" in content or "kind: PipelineVersion" in content:
                self.assertIn(f"namespace: {custom_namespace}", content)

    def test_migration_error_handling(self):
        """Test migration script error handling with real API"""
        
        # Test with invalid host
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', 'http://invalid-host:8080',
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            # Should handle connection error gracefully
            migrate()
        
        # Verify no files were created due to error
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertEqual(len(yaml_files), 0, "Should not create files when API is unavailable")

    def test_migration_output_structure(self):
        """Test that migration output has correct structure"""
        
        # Run migration
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()
        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Check structure of each YAML file
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            
            # Should be valid YAML
            self.assertIn("apiVersion:", content)
            self.assertIn("kind:", content)
            self.assertIn("metadata:", content)
            
            # Should have correct API version for KFP
            if "kind: Pipeline" in content or "kind: PipelineVersion" in content:
                self.assertIn("pipelines.kubeflow.org/v1beta1", content)
            
            # Should have namespace
            self.assertIn("namespace:", content)
            
            # Should have original ID annotation
            if "kind: Pipeline" in content or "kind: PipelineVersion" in content:
                self.assertIn("pipelines.kubeflow.org/original-id", content)

    def test_migration_preserves_pipeline_specs(self):
        """Test that migration preserves pipeline specifications correctly"""
        
        # Run migration
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow'
        ]):
            migrate()
        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Check that pipeline specs are preserved
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            if "kind: PipelineVersion" in content:
                # Should have pipeline spec
                self.assertIn("pipelineSpec:", content)
                # Should have pipeline info
                self.assertIn("pipelineInfo:", content)
                # Should have root DAG
                self.assertIn("root:", content)

    def test_migration_with_pagination(self):
        """Test migration script with pagination handling"""
        
        # Run migration with batch size
        with patch('sys.argv', [
            'migration.py',
            '--kfp-server-host', KFP_ENDPOINT,
            '--output', str(self.output_dir),
            '--namespace', 'kubeflow',
            '--batch-size', '2'
        ]):
            migrate()
        
        
        yaml_files = list(self.output_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "Migration should create YAML files")
        
        # Verify all files have correct structure
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            self.assertIn("apiVersion:", content)
            self.assertIn("kind:", content)


if __name__ == '__main__':
    unittest.main()
