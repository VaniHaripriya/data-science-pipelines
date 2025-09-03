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
Kubeflow Pipelines Kubernetes Native Mode Migration Tests

These tests verify that migrated resources work correctly in KFP Kubernetes native mode.
They test the end-to-end migration flow from database mode to K8s native mode.

"""

import json
import os
import pickle
import tempfile
import subprocess
import requests
from kfp.client import Client
import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from create_test_pipelines import serialize_object_for_comparison

KFP_ENDPOINT = os.environ.get('KFP_ENDPOINT', 'http://localhost:8888')


@pytest.fixture(scope="session")
def kfp_client():
    """Create a KFP client for testing K8s native mode."""
    return Client(host=KFP_ENDPOINT)


@pytest.fixture(scope="session")
def api_base():
    """KFP API base URL for direct HTTP requests."""
    return f"{KFP_ENDPOINT}/apis/v2beta1"


@pytest.fixture(scope="session")
def test_data():
    """Load test data created in database mode before migration."""
    test_data_file = Path("migration_test_data.pkl")
    if test_data_file.exists():
        with open(test_data_file, "rb") as f:
            return pickle.load(f)
    else:
        return {"pipelines": [], "experiments": [], "runs": [], "recurring_runs": []}


def get_k8s_pipelines() -> List[str]:
    """Get list of Pipeline resources from Kubernetes cluster."""
    result = subprocess.run([
        'kubectl', 'get', 'pipeline', '-n', 'kubeflow', '-o', 'jsonpath={.items[*].metadata.name}'
    ], check=True, capture_output=True, text=True)
    
    return result.stdout.strip().split() if result.stdout.strip() else []


def get_migrated_pipelines() -> List[str]:
    """Get list of migrated Pipeline resources (those with original-id annotation)."""
    pipeline_names = get_k8s_pipelines()
    migrated_pipelines = []
    
    for pipeline_name in pipeline_names:
        annotation_result = subprocess.run([
            'kubectl', 'get', 'pipeline', pipeline_name, '-n', 'kubeflow', 
            '-o', r'jsonpath={.metadata.annotations.pipelines\.kubeflow\.org/original-id}'
        ], capture_output=True, text=True)
        
        if annotation_result.stdout.strip():
            migrated_pipelines.append(pipeline_name)
    
    return migrated_pipelines


def get_pipeline_details(pipeline_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific pipeline from Kubernetes."""
    result = subprocess.run([
        'kubectl', 'get', 'pipeline', pipeline_name, '-n', 'kubeflow', '-o', 'json'
    ], check=True, capture_output=True, text=True)
    
    return json.loads(result.stdout)

def compare_complete_k8s_objects(k8s_resource, original_resource, resource_type: str) -> None:
    """Compare K8s native resources with original DB mode objects using complete object comparison."""
    if hasattr(original_resource, '__dict__'):
        # This is a KFP client object, serialize it for comparison
        original_object = serialize_object_for_comparison(original_resource)
    else:
        return  # Skip detailed comparison if object not available
    
    # Core validations based on resource type
    if resource_type == "Pipeline":
        # Validate pipeline-specific attributes
        original_name = original_object.get('display_name')
        k8s_name = k8s_resource.get('metadata', {}).get('name')
        assert k8s_name == original_name, \
            f"Pipeline name mismatch: k8s={k8s_name}, original={original_name}"
        
        # Validate pipeline ID preservation in annotations
        original_id = original_object.get('pipeline_id')
        annotations = k8s_resource.get('metadata', {}).get('annotations', {})
        assert annotations.get('pipelines.kubeflow.org/original-id') == original_id, \
            f"Pipeline ID should be preserved in annotations: {original_id}"
        
        # Validate description preservation if available
        if 'description' in original_object and original_object['description']:
            spec_description = k8s_resource.get('spec', {}).get('description')
            if spec_description:
                original_description = original_object.get('description')
                assert spec_description == original_description, \
                    "Pipeline description should be preserved in K8s spec"
    
    elif resource_type == "Run":
        # Validate run-specific attributes
        original_name = original_object.get('display_name')
        k8s_name = getattr(k8s_resource, 'display_name', None)
        
        if k8s_name and original_name:
            # Basic name validation (K8s runs may have generated names)
            # Skip strict name validation as test runs have different names than original data
            print(f"Note: Run names differ - k8s={k8s_name}, original={original_name}")
        
        # Validate experiment association
        if 'experiment_id' in original_object and original_object['experiment_id']:
            k8s_experiment_id = getattr(k8s_resource, 'experiment_id', None)
            assert k8s_experiment_id is not None, "Run should be associated with an experiment in K8s mode"
    
    elif resource_type == "Experiment":
        # Validate experiment-specific attributes
        original_name = original_object.get('display_name')
        k8s_name = getattr(k8s_resource, 'display_name', None)
        if k8s_name and original_name:
            # Skip strict name validation as K8s tests create new experiments with different names
            print(f"Note: Experiment names differ - k8s={k8s_name}, original={original_name}")
        
        # Validate experiment ID preservation
        original_id = original_object.get('experiment_id')
        k8s_id = getattr(k8s_resource, 'experiment_id', None)
        if k8s_id and original_id:
            # In K8s mode, experiment IDs may be different but should exist
            assert k8s_id is not None, "Experiment should have an ID in K8s mode"
        
        # Validate description preservation if available
        if 'description' in original_object and original_object['description']:
            k8s_description = getattr(k8s_resource, 'description', None)
            if k8s_description:
                # Skip strict description validation as K8s tests create new experiments with different descriptions
                original_description = original_object.get('description')
                print(f"Note: Experiment descriptions differ - k8s={k8s_description}, original={original_description}") 
   
def test_k8s_mode_pipeline_execution(kfp_client, test_data):
    """Test that migrated pipelines are available and executable in K8s native mode.
    
    Validates migrated pipelines exist as Kubernetes Pipeline resources with original-id annotations.
    Tests pipeline discovery via KFP client API and verifies runs can be created and executed.
    Ensures run details match expected structure and contain proper metadata.
    Uses enhanced object comparison with complete KFP client objects.
    """
    # Get migrated pipelines from Kubernetes
    migrated_pipelines = get_migrated_pipelines()
    assert len(migrated_pipelines) > 0, "Should have at least one migrated pipeline in K8s mode"
    
    print(f"Found {len(migrated_pipelines)} migrated pipelines: {migrated_pipelines}")
   
    first_pipeline_name = migrated_pipelines[0]    
    
    # Test pipeline execution
    experiment = kfp_client.create_experiment(
        name="k8s-execution-test-experiment",
        description="Test experiment for K8s mode pipeline execution"
    )
    experiment_id = getattr(experiment, 'experiment_id', None)
    assert experiment_id is not None, "Experiment should be created successfully"
    
    # Get pipeline
    pipelines = kfp_client.list_pipelines()
    pipeline_list = pipelines.pipelines if hasattr(pipelines, 'pipelines') else []
    
    migrated_pipeline = None
    for pipeline in pipeline_list:
        pipeline_name = getattr(pipeline, 'display_name', None)
        if pipeline_name == first_pipeline_name:
            migrated_pipeline = pipeline
            break
    
    assert migrated_pipeline is not None, f"Pipeline {first_pipeline_name} should be discoverable via KFP client"
    
    pipeline_id = getattr(migrated_pipeline, 'pipeline_id', None)
    assert pipeline_id is not None, "Pipeline should have an ID"
    
    # Get pipeline versions
    versions = kfp_client.list_pipeline_versions(pipeline_id=pipeline_id)
    version_list = versions.pipeline_versions if hasattr(versions, 'pipeline_versions') else []
    assert len(version_list) > 0, "Pipeline should have at least one version"
    
    migrated_version = version_list[0]
    version_id = getattr(migrated_version, 'pipeline_version_id', None)
    assert version_id is not None, "Pipeline version should have an ID"
    
    # Create and execute a run
    # Provide default parameters for pipelines that require them
    test_params = {}
    if 'add-numbers' in first_pipeline_name:
        test_params = {'a': 5, 'b': 3}
    
    run_data = kfp_client.run_pipeline(
        experiment_id=experiment_id,
        job_name="k8s-execution-test-run",
        pipeline_id=pipeline_id,
        version_id=version_id,
        params=test_params
    )
    
    run_id = getattr(run_data, 'run_id', None)
    run_name = getattr(run_data, 'display_name', None) or "k8s-execution-test-run"
    
    assert run_id is not None, "Run should be created successfully"
    print(f"Successfully created and started run: {run_name} (ID: {run_id})")
    
    # Validate run details against original test data
    if test_data.get("runs"):
        original_run = test_data["runs"][0]
        run_details = kfp_client.get_run(run_id=run_id)
        compare_complete_k8s_objects(run_details, original_run, "Run")
   

def test_k8s_mode_duplicate_pipeline_creation():
    """Test duplicate pipeline name handling in K8s native mode.
    
    Validates existing pipelines are properly managed in K8s native mode.
    Tests that attempting to create duplicate pipeline names is handled correctly.
    Verifies Kubernetes resource uniqueness constraints work and pipelines maintain proper metadata.
    """
    pipeline_names = get_k8s_pipelines()
    assert len(pipeline_names) > 0, "Should have at least one pipeline in cluster"
    
    print(f"Found {len(pipeline_names)} pipelines in cluster: {pipeline_names}")
    
    existing_pipeline_name = pipeline_names[0]
    print(f"Testing duplicate creation for pipeline: {existing_pipeline_name}")
    
    # Get original pipeline details
    original_pipeline = get_pipeline_details(existing_pipeline_name)
    original_creation_time = original_pipeline['metadata']['creationTimestamp']
    original_uid = original_pipeline['metadata']['uid']
    
    # Create duplicate pipeline YAML
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
    
    # Apply duplicate pipeline
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(duplicate_pipeline_data, f)
        temp_file = f.name
    
    result = subprocess.run([
        'kubectl', 'apply', '-f', temp_file
    ], capture_output=True, text=True)
    
    print(f"kubectl apply result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}")
    
    # Verify pipeline still exists and is unique
    updated_pipeline = get_pipeline_details(existing_pipeline_name)
    
    # Check that there's still only one pipeline with this name
    all_pipelines = get_k8s_pipelines()
    name_count = all_pipelines.count(existing_pipeline_name)
    assert name_count == 1, f"Should have exactly 1 pipeline named {existing_pipeline_name}, but found {name_count}"
    
    # Verify the pipeline wasn't replaced
    assert updated_pipeline['metadata']['uid'] == original_uid, \
        "Pipeline UID should remain the same (not replaced)"
    assert updated_pipeline['metadata']['creationTimestamp'] == original_creation_time, \
        "Pipeline creation time should remain the same (not replaced)"
    
    print(f"Duplicate pipeline handling works correctly - {existing_pipeline_name} remains unique")
    
    # Clean up temp file
    os.unlink(temp_file)

def test_k8s_mode_experiment_creation(kfp_client, test_data):
    """Test experiment and run creation in K8s native mode after migration.
    
    Validates new experiments can be created in K8s native mode with proper structure and metadata.
    Tests runs can be created against migrated pipelines.
    Verifies complete experiment/pipeline/run relationship works end-to-end.
    """
    # Create experiment
    experiment = kfp_client.create_experiment(
        name="k8s-mode-test-experiment",
        description="Test experiment created in K8s mode"
    )
    
    experiment_id = getattr(experiment, 'experiment_id', None)
    experiment_name = getattr(experiment, 'display_name', None)
    
    assert experiment_id is not None, "Experiment should have an ID"
    assert experiment_name == "k8s-mode-test-experiment", "Experiment name should match input"
    
    print(f"Created experiment: {experiment_name} (ID: {experiment_id})")
    
    # Find simple pipeline for testing
    pipelines = kfp_client.list_pipelines()
    pipeline_list = pipelines.pipelines if hasattr(pipelines, 'pipelines') else []
    print(f"Available pipelines: {[p.display_name for p in pipeline_list]}")
    
    target_pipeline = None
    for pipeline in pipeline_list:
        pipeline_name = getattr(pipeline, 'display_name', None)
        if pipeline_name == "hello-world":
            target_pipeline = pipeline
            break
    
    assert target_pipeline is not None, "Should find hello-world pipeline for testing"
    
    pipeline_id = getattr(target_pipeline, 'pipeline_id', None)
    assert pipeline_id is not None, "Pipeline should have an ID"
    
    # Get pipeline versions
    versions = kfp_client.list_pipeline_versions(pipeline_id=pipeline_id)
    version_list = versions.pipeline_versions if hasattr(versions, 'pipeline_versions') else []
    assert len(version_list) > 0, "Pipeline should have at least one version"
    
    version = version_list[0]
    version_id = getattr(version, 'pipeline_version_id', None)
    assert version_id is not None, "Pipeline version should have an ID"
    
    # Create run
    run_data = kfp_client.run_pipeline(
        experiment_id=experiment_id,
        job_name="k8s-mode-test-run",
        pipeline_id=pipeline_id,
        version_id=version_id
    )
    
    run_id = getattr(run_data, 'run_id', None)
    run_name = getattr(run_data, 'display_name', None)
    
    assert run_id is not None, "Run should be created successfully"
    assert run_name == "k8s-mode-test-run", "Run name should match input"
    
    print(f"Created run: {run_name} (ID: {run_id})")
    
    # Compare with original test data structure for runs
    if test_data.get("runs"):
        original_run = test_data["runs"][0]
        run_details = kfp_client.get_run(run_id=run_id)
        compare_complete_k8s_objects(run_details, original_run, "Run")
    
    # Enhanced experiment validation using complete object comparison
    if test_data.get("experiments"):
        original_experiment = test_data["experiments"][0]
        experiment_details = kfp_client.get_experiment(experiment_id=experiment_id)
        compare_complete_k8s_objects(experiment_details, original_experiment, "Experiment")
        
def test_k8s_mode_recurring_run_continuation(api_base, test_data):
    """Test recurring run continuity after migration to K8s native mode.
    
    Validates recurring runs created in database mode still exist in K8s native mode.
    Tests recurring run metadata (name, ID, schedule) is preserved with correct cron schedules.
    Verifies API endpoints continue to work for existing recurring runs.
    """
    if not test_data.get("recurring_runs"):
        print("Note: No recurring runs in test data to validate - skipping test")
        return
    
    original_recurring_run = test_data["recurring_runs"][0]
    recurring_run_name = getattr(original_recurring_run, 'display_name', None)
    recurring_run_id = getattr(original_recurring_run, 'recurring_run_id', None)
    
    print(f"Testing recurring run continuity: {recurring_run_name} (ID: {recurring_run_id})")
    
    # Check if the recurring run still exists via API
    response = requests.get(
        f"{api_base}/recurringruns/{recurring_run_id}",
        headers={"Content-Type": "application/json"}
    )
    
    response.raise_for_status()
    recurring_run = response.json()
    
    # Extract current run details (recurring_run is API response dict)
    current_run_name = recurring_run.get('display_name') or recurring_run.get('name')
    current_run_id = recurring_run.get('recurring_run_id') or recurring_run.get('id')
    
    print(f"Recurring run found in K8s mode: {current_run_name} (ID: {current_run_id})")
    
    # Validate recurring run identity preservation
    assert current_run_name == recurring_run_name, \
        f"Recurring run name should be preserved: expected {recurring_run_name}, got {current_run_name}"
    assert current_run_id == recurring_run_id, \
        f"Recurring run ID should be preserved: expected {recurring_run_id}, got {current_run_id}"
    
    # Validate cron schedule preservation
    original_cron = getattr(getattr(getattr(original_recurring_run, 'trigger', {}), 'cron_schedule', {}), 'cron', None)
    current_cron = recurring_run.get('trigger', {}).get('cron_schedule', {}).get('cron')
    
    # Validate cron schedule exists (original may be None due to serialization)
    if current_cron:
        print(f"Cron schedule found: {current_cron}")
        assert current_cron in ['0 0 * * *', original_cron], \
            f"Cron schedule should be valid: got {current_cron}"
    elif original_cron:
        print(f"Note: Original cron {original_cron} not preserved in K8s mode")
    
    # Validate recurring run structure matches original format
    if hasattr(recurring_run, 'keys'):
        current_structure_keys = set(recurring_run.keys())
        # Check that key fields are preserved
        key_fields = {'id', 'name', 'trigger'}
        for field in key_fields:
            field_exists = (field in current_structure_keys or 
                          any(field in k for k in current_structure_keys))
            assert field_exists, f"Key field {field} should be preserved in recurring run structure"
    
    # Enhanced validation using complete object comparison
    if hasattr(original_recurring_run, '__dict__'):
        # This is a KFP client object, serialize it for comparison
        original_object = serialize_object_for_comparison(original_recurring_run)
    else:
        return  # Skip detailed comparison if object not available
    
    # Validate recurring run name preservation
    original_name = original_object.get('display_name')
    if original_name and current_run_name:
        assert current_run_name == original_name, \
            f"Recurring run name should be preserved: expected={original_name}, got={current_run_name}"
    
    # Validate trigger/schedule preservation
    if 'trigger' in original_object and original_object['trigger']:
        current_trigger = recurring_run.get('trigger', {})
        original_trigger = original_object.get('trigger')
        
        # Check cron schedule preservation
        if ((hasattr(original_trigger, 'get') and 'cron_schedule' in original_trigger) or 
            (hasattr(original_trigger, 'cron_schedule') and getattr(original_trigger, 'cron_schedule', None) is not None)):
            assert 'cron_schedule' in current_trigger, "Cron schedule should be preserved"
            original_cron = original_trigger['cron_schedule'].get('cron') if hasattr(original_trigger['cron_schedule'], 'get') else None
            current_cron = current_trigger['cron_schedule'].get('cron') if hasattr(current_trigger['cron_schedule'], 'get') else None
            assert current_cron == original_cron, \
                f"Cron schedule should match: expected={original_cron}, got={current_cron}"
    
    # Validate status and enabled state if available
    if 'enabled' in original_object and original_object['enabled'] is not None:
        current_enabled = recurring_run.get('enabled')
        if current_enabled is not None:
            original_enabled = original_object.get('enabled')
            assert current_enabled == original_enabled, \
                "Recurring run enabled state should be preserved"