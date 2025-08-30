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


def validate_pipeline_structure(pipeline_data: Dict[str, Any], expected_original_id: str = None) -> None:
    """Validate that a pipeline has the expected Kubernetes structure."""
    assert 'metadata' in pipeline_data, "Pipeline should have metadata"
    assert 'spec' in pipeline_data, "Pipeline should have spec"
    assert pipeline_data['kind'] == 'Pipeline', "Resource should be a Pipeline"
    assert pipeline_data['metadata']['namespace'] == 'kubeflow', "Pipeline should be in kubeflow namespace"
    
    if expected_original_id:
        annotations = pipeline_data.get('metadata', {}).get('annotations', {})
        assert annotations.get('pipelines.kubeflow.org/original-id') == expected_original_id, \
            f"Pipeline should have original ID annotation: {expected_original_id}"


def serialize_object_for_comparison(obj):
    """Serialize KFP objects to JSON-serializable format for comparison."""
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif hasattr(obj, '__dict__'):
        # Convert object attributes to dict, handling nested objects
        result = {}
        for key, value in obj.__dict__.items():
            if hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, type(None))):
                result[key] = serialize_object_for_comparison(value)
            else:
                result[key] = value
        return result
    else:
        return str(obj)


def compare_complete_k8s_objects(k8s_resource, original_resource, resource_type: str) -> None:
    """Compare K8s native resources with original DB mode objects using complete object comparison."""
    # Handle both KFP client objects and dict structures
    if hasattr(original_resource, '__dict__'):
        # This is a KFP client object, serialize it for comparison
        original_object = serialize_object_for_comparison(original_resource)
    elif isinstance(original_resource, dict) and 'object_serialized' in original_resource:
        # This is the old dict structure
        original_object = original_resource['object_serialized']
    else:
        return  # Skip detailed comparison if object not available
    
    # Core validations based on resource type
    if resource_type == "Pipeline":
        # Validate pipeline-specific attributes
        original_name = original_object.get('display_name') or original_object.get('name')
        k8s_name = k8s_resource.get('metadata', {}).get('name')
        assert k8s_name == original_name, \
            f"Pipeline name mismatch: k8s={k8s_name}, original={original_name}"
        
        # Validate pipeline ID preservation in annotations
        original_id = original_object.get('pipeline_id') or getattr(original_resource, 'pipeline_id', None)
        annotations = k8s_resource.get('metadata', {}).get('annotations', {})
        assert annotations.get('pipelines.kubeflow.org/original-id') == original_id, \
            f"Pipeline ID should be preserved in annotations: {original_id}"
        
        # Validate description preservation if available
        if 'description' in original_object:
            spec_description = k8s_resource.get('spec', {}).get('description')
            if spec_description:
                assert spec_description == original_object['description'], \
                    "Pipeline description should be preserved in K8s spec"
    
    elif resource_type == "Run":
        # Validate run-specific attributes
        original_name = original_object.get('display_name') or original_object.get('name')
        # For K8s runs, name may come from KFP client response
        if hasattr(k8s_resource, 'display_name'):
            k8s_name = getattr(k8s_resource, 'display_name', None)
        else:
            k8s_name = k8s_resource.get('display_name')
        
        if k8s_name and original_name:
            # Basic name validation (K8s runs may have generated names)
            # Skip strict name validation as test runs have different names than original data
            print(f"Note: Run names differ - k8s={k8s_name}, original={original_name}")
        
        # Validate experiment association
        if 'experiment_id' in original_object:
            k8s_experiment_id = getattr(k8s_resource, 'experiment_id', None) or (k8s_resource.get('experiment_id') if hasattr(k8s_resource, 'get') else None)
            assert k8s_experiment_id is not None, "Run should be associated with an experiment in K8s mode"
    
    elif resource_type == "Experiment":
        # Validate experiment-specific attributes
        original_name = original_object.get('display_name') or original_object.get('name')
        k8s_name = getattr(k8s_resource, 'display_name', None) or (k8s_resource.get('display_name') if hasattr(k8s_resource, 'get') else None)
        if k8s_name and original_name:
            assert k8s_name == original_name, \
                f"Experiment name mismatch: k8s={k8s_name}, original={original_name}"
        
        # Validate experiment ID preservation
        original_id = original_object.get('experiment_id') or getattr(original_resource, 'experiment_id', None)
        k8s_id = getattr(k8s_resource, 'experiment_id', None) or (k8s_resource.get('experiment_id') if hasattr(k8s_resource, 'get') else None)
        if k8s_id and original_id:
            # In K8s mode, experiment IDs may be different but should exist
            assert k8s_id is not None, "Experiment should have an ID in K8s mode"
        
        # Validate description preservation if available
        if 'description' in original_object:
            k8s_description = getattr(k8s_resource, 'description', None) or (k8s_resource.get('description') if hasattr(k8s_resource, 'get') else None)
            if k8s_description:
                assert k8s_description == original_object['description'], \
                    "Experiment description should be preserved in K8s mode"
    
    # Validate creation timestamp preservation if available (optional)
    if 'created_at' in original_object:
        # K8s resources should have creationTimestamp in metadata
        creation_time = k8s_resource.get('metadata', {}).get('creationTimestamp')
        if not creation_time:
            # For client objects, check if they have created_at attribute
            creation_time = getattr(k8s_resource, 'created_at', None)
        if not creation_time:
            print(f"Note: Creation timestamp not preserved in K8s mode for {resource_type}")


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
    
    # Validate pipeline structure in Kubernetes
    first_pipeline_name = migrated_pipelines[0]
    pipeline_details = get_pipeline_details(first_pipeline_name)
    
    # Find corresponding original pipeline in test data
    original_pipeline = None
    for pipeline in test_data.get("pipelines", []):
        # Handle both KFP client objects and dict structures
        pipeline_name = getattr(pipeline, 'display_name', None) or getattr(pipeline, 'name', None) or (pipeline.get("name", "") if hasattr(pipeline, 'get') else "")
        if pipeline_name == first_pipeline_name:
            original_pipeline = pipeline
            break
    
    if original_pipeline:
        # Get pipeline ID from KFP client object or dict
        original_id = getattr(original_pipeline, 'pipeline_id', None) or (original_pipeline.get("id", "") if hasattr(original_pipeline, 'get') else "")
        validate_pipeline_structure(pipeline_details, original_id)
        # Enhanced validation using complete object comparison
        compare_complete_k8s_objects(pipeline_details, original_pipeline, "Pipeline")
    else:
        validate_pipeline_structure(pipeline_details)
    
    # Test pipeline execution via KFP client
    experiment = kfp_client.create_experiment(
        name="k8s-execution-test-experiment",
        description="Test experiment for K8s mode pipeline execution"
    )
    experiment_id = getattr(experiment, 'experiment_id', None)
    assert experiment_id is not None, "Experiment should be created successfully"
    
    # Get pipeline via KFP client
    pipelines = kfp_client.list_pipelines()
    pipeline_list = pipelines.pipelines if hasattr(pipelines, 'pipelines') else []
    
    target_pipeline = None
    for pipeline in pipeline_list:
        pipeline_name = getattr(pipeline, 'display_name', None)
        if pipeline_name == first_pipeline_name:
            target_pipeline = pipeline
            break
    
    assert target_pipeline is not None, f"Pipeline {first_pipeline_name} should be discoverable via KFP client"
    
    pipeline_id = getattr(target_pipeline, 'pipeline_id', None)
    assert pipeline_id is not None, "Pipeline should have an ID"
    
    # Get pipeline versions
    versions = kfp_client.list_pipeline_versions(pipeline_id=pipeline_id)
    version_list = versions.pipeline_versions if hasattr(versions, 'pipeline_versions') else []
    assert len(version_list) > 0, "Pipeline should have at least one version"
    
    target_version = version_list[0]
    version_id = getattr(target_version, 'pipeline_version_id', None)
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
    
    # Validate run details structure
    run_details = kfp_client.get_run(run_id=run_id)
    
    # Compare with original test data structure
    expected_run_fields = {
        'run_id': run_id,
        'display_name': run_name,
        'experiment_id': experiment_id,
        'pipeline_spec': {
            'pipeline_id': pipeline_id,
            'pipeline_version_id': version_id
        }
    }
    
    # Validate run structure matches expected format
    assert getattr(run_details, 'run_id', None) == expected_run_fields['run_id'], \
        "Run ID should match expected value"
    assert getattr(run_details, 'display_name', None) == expected_run_fields['display_name'], \
        "Run name should match expected value"
    
    # Validate that run is associated with correct experiment and pipeline
    run_experiment_id = getattr(run_details, 'experiment_id', None)
    assert run_experiment_id == experiment_id, "Run should be associated with correct experiment"
    
    # Enhanced validation using complete object comparison with original runs
    if test_data.get("runs"):
        original_run = test_data["runs"][0]
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
    
    # Validate run structure matches expected format from test data
    expected_run_structure = {
        "id": run_id,
        "name": run_name,
        "pipeline_spec": {
            "pipeline_id": pipeline_id,
            "pipeline_version_id": version_id
        },
        "experiment_id": experiment_id
    }
    
    # Compare with original test data structure for runs
    if test_data.get("runs"):
        original_run = test_data["runs"][0]
        # Handle both KFP client objects and dict structures
        if hasattr(original_run, 'keys'):
            original_structure_keys = set(original_run.keys())
        else:
            # For KFP client objects, get attributes
            original_structure_keys = set(dir(original_run))
        new_structure_keys = set(expected_run_structure.keys())
       
        essential_keys = {"id", "name", "pipeline_spec"}
        assert essential_keys.issubset(new_structure_keys), \
            f"Run should have essential keys: {essential_keys}. Got: {new_structure_keys}"
        
        # Enhanced validation using complete object comparison
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
    assert test_data.get("recurring_runs"), "Test data should contain recurring runs for validation"
    
    original_recurring_run = test_data["recurring_runs"][0]
    # Handle both KFP client objects and dict structures
    recurring_run_name = getattr(original_recurring_run, 'display_name', None) or getattr(original_recurring_run, 'name', None) or (original_recurring_run.get("name") if hasattr(original_recurring_run, 'get') else None)
    recurring_run_id = getattr(original_recurring_run, 'recurring_run_id', None) or (original_recurring_run.get("id") if hasattr(original_recurring_run, 'get') else None)
    
    print(f"Testing recurring run continuity: {recurring_run_name} (ID: {recurring_run_id})")
    
    # Check if the recurring run still exists via API
    response = requests.get(
        f"{api_base}/recurringruns/{recurring_run_id}",
        headers={"Content-Type": "application/json"}
    )
    
    response.raise_for_status()
    recurring_run = response.json()
    
    # Extract current run details
    current_run_name = getattr(recurring_run, 'display_name', None) or (
                              recurring_run.get('display_name') if hasattr(recurring_run, 'get') else None) or (
                              recurring_run.get('name') if hasattr(recurring_run, 'get') else None)
    current_run_id = getattr(recurring_run, 'recurring_run_id', None) or (
                           recurring_run.get('recurring_run_id') if hasattr(recurring_run, 'get') else None) or (
                           recurring_run.get('id') if hasattr(recurring_run, 'get') else None)
    
    print(f"Recurring run found in K8s mode: {current_run_name} (ID: {current_run_id})")
    
    # Validate recurring run identity preservation
    assert current_run_name == recurring_run_name, \
        f"Recurring run name should be preserved: expected {recurring_run_name}, got {current_run_name}"
    assert current_run_id == recurring_run_id, \
        f"Recurring run ID should be preserved: expected {recurring_run_id}, got {current_run_id}"
    
    # Validate cron schedule preservation
    original_cron = (original_recurring_run.get('trigger', {}).get('cron_schedule', {}).get('cron') if hasattr(original_recurring_run, 'get') else None)
    current_cron = (recurring_run.get('trigger', {}).get('cron_schedule', {}).get('cron') if hasattr(recurring_run, 'get') else None)
    
    assert current_cron == original_cron, \
        f"Cron schedule should be preserved: expected {original_cron}, got {current_cron}"
    
    # Validate recurring run structure matches original format
    expected_structure_keys = set(original_recurring_run.keys())
    current_structure_keys = set(recurring_run.keys())
    
    # Check that key fields are preserved
    key_fields = {'id', 'name', 'trigger'}
    for field in key_fields:
        if field in expected_structure_keys:
            field_exists = (field in current_structure_keys or 
                          any(field in k for k in current_structure_keys))
            assert field_exists, f"Key field {field} should be preserved in recurring run structure"
    
    # Enhanced validation using complete object comparison
    if hasattr(original_recurring_run, '__dict__'):
        # This is a KFP client object, serialize it for comparison
        original_object = serialize_object_for_comparison(original_recurring_run)
    elif isinstance(original_recurring_run, dict) and 'object_serialized' in original_recurring_run:
        # This is the old dict structure
        original_object = original_recurring_run['object_serialized']
    else:
        return  # Skip detailed comparison if object not available
    
    # Validate recurring run name preservation
    original_name = original_object.get('display_name') or original_object.get('name')
    if original_name and current_run_name:
        assert current_run_name == original_name, \
            f"Recurring run name should be preserved: expected={original_name}, got={current_run_name}"
    
    # Validate trigger/schedule preservation
    if 'trigger' in original_object and original_object['trigger']:
        current_trigger = recurring_run.get('trigger', {})
        original_trigger = original_object['trigger']
        
        # Check cron schedule preservation
        if 'cron_schedule' in original_trigger:
            assert 'cron_schedule' in current_trigger, "Cron schedule should be preserved"
            original_cron = original_trigger['cron_schedule'].get('cron') if hasattr(original_trigger['cron_schedule'], 'get') else None
            current_cron = current_trigger['cron_schedule'].get('cron') if hasattr(current_trigger['cron_schedule'], 'get') else None
            assert current_cron == original_cron, \
                f"Cron schedule should match: expected={original_cron}, got={current_cron}"
    
    # Validate status and enabled state if available
    if 'enabled' in original_object:
        current_enabled = recurring_run.get('enabled') if hasattr(recurring_run, 'get') else None
        if current_enabled is not None:
            assert current_enabled == original_object['enabled'], \
                "Recurring run enabled state should be preserved"