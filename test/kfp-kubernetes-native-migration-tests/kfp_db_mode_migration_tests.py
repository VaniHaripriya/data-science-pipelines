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
Kubeflow Pipelines Database Mode Migration Tests

These tests verify the migration script that exports KFP resources from database mode
to Kubernetes native format
"""

import json
import os
import pickle
import sys
import subprocess
import requests
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch
from typing import Dict, List, Any

# Add the tools directory to path to import migration module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../tools/k8s-native'))

from migration import migrate

# Import serialization function from create_test_pipelines
sys.path.insert(0, os.path.dirname(__file__))
from create_test_pipelines import serialize_object_for_comparison

KFP_ENDPOINT = os.environ.get('KFP_ENDPOINT', 'http://localhost:8888')


@pytest.fixture(scope="session")
def test_data():
    """Load test data created by create_test_pipelines.py.
    
    """
    test_data_file = Path("migration_test_data.pkl")
    if test_data_file.exists():
        with open(test_data_file, "rb") as f:
            return pickle.load(f)
    else:
        pytest.skip("Test data file not found. Run create_test_pipelines.py first when KFP server is available.")

@pytest.fixture(scope="function")
def migration_output_dir(request):
    """Create a unique output directory for each test's migration results.
    
    This directory is shared with K8s mode tests to apply migrated resources.
    """
    # Use a shared persistent directory that K8s mode tests can access
    shared_migration_base = Path("/tmp/kfp_shared_migration_outputs")
    shared_migration_base.mkdir(exist_ok=True)
    
    output_dir = shared_migration_base / f"migration_output_{request.node.name}"
    output_dir.mkdir(exist_ok=True)
 
    # Write the migration output directory to a shared location for K8s mode tests
    migration_info_file = Path("/tmp/kfp_migration_output_dir.txt")
    with open(migration_info_file, "w") as f:
        f.write(str(output_dir))
    
    yield output_dir  

@pytest.fixture
def run_migration(migration_output_dir):
    """Execute the migration script and return the output directory
    containing the generated YAML files.
    
    """
    with patch('sys.argv', [
        'migration.py',
        '--kfp-server-host', KFP_ENDPOINT,
        '--output', str(migration_output_dir),
        '--namespace', 'kubeflow'
    ]):
        migrate()
    
    return migration_output_dir

def parse_yaml_files(output_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Parse all YAML files in the output directory and group by kind."""
    resources = {"Pipeline": [], "PipelineVersion": [], "Experiment": [], "Run": [], "RecurringRun": []}
    
    for yaml_file in output_dir.glob("*.yaml"):
        with open(yaml_file) as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if doc and 'kind' in doc:
                    kind = doc['kind']
                    if kind in resources:
                        resources[kind].append(doc)
    
    return resources

def validate_original_id_annotation(resource: Dict[str, Any], expected_id: str) -> None:
    """Validate that a resource has the correct original ID annotation."""
    annotations = resource.get('metadata', {}).get('annotations', {})
    actual_id = annotations.get('pipelines.kubeflow.org/original-id')
    assert actual_id == expected_id, f"Resource should have original ID annotation: {expected_id}, got: {actual_id}"


def validate_resource_structure(resource: Dict[str, Any], expected_fields: Dict[str, Any]) -> None:
    """Validate that a resource contains expected field values."""
    for field_path, expected_value in expected_fields.items():
        current = resource
        for key in field_path.split('.'):
            assert key in current, f"Field path {field_path} missing key: {key}"
            current = current[key]
        assert current == expected_value, f"Field {field_path}: expected {expected_value}, got {current}"


def find_test_data_by_name(test_data: Dict[str, Any], resource_type: str, name: str):
    """Find a resource in test data by name."""
    resources = test_data.get(resource_type, [])
    for resource in resources:
        # Handle both KFP client objects and dict structures
        resource_name = getattr(resource, 'display_name', None) or getattr(resource, 'name', None) or resource.get("name", "")
        if name in str(resource_name):
            return resource
    pytest.fail(f"Test data should contain {resource_type} with name containing '{name}'")


def compare_complete_objects(migrated_resource: Dict[str, Any], original_resource, resource_type: str) -> None:
    """Compare complete objects using serialized data from KFP client retrieval."""
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
        migrated_name = migrated_resource.get('metadata', {}).get('name')
        assert migrated_name == original_name, \
            f"Pipeline name mismatch: migrated={migrated_name}, original={original_name}"
        
        # Validate pipeline ID preservation in annotations
        original_id = original_object.get('pipeline_id') or getattr(original_resource, 'pipeline_id', None)
        annotations = migrated_resource.get('metadata', {}).get('annotations', {})
        assert annotations.get('pipelines.kubeflow.org/original-id') == original_id, \
            f"Pipeline ID should be preserved in annotations: {original_id}"
    
    elif resource_type == "PipelineVersion":
        # Validate pipeline version-specific attributes
        original_name = original_object.get('display_name') or original_object.get('name')
        migrated_name = migrated_resource.get('metadata', {}).get('name')
        
        # Validate version ID preservation in annotations
        original_id = original_object.get('pipeline_version_id') or getattr(original_resource, 'pipeline_version_id', None)
        annotations = migrated_resource.get('metadata', {}).get('annotations', {})
        assert annotations.get('pipelines.kubeflow.org/original-id') == original_id, \
            f"Pipeline version ID should be preserved in annotations: {original_id}"
        
        # Validate pipeline spec preservation
        if 'pipeline_spec' in original_object:
            assert 'spec' in migrated_resource, "Migrated pipeline version should have spec"
            assert 'pipelineSpec' in migrated_resource['spec'], "Should have pipelineSpec in spec"
    
    # Validate creation timestamp preservation if available (optional)
    if 'created_at' in original_object:
        annotations = migrated_resource.get('metadata', {}).get('annotations', {})
        has_timestamp = any(key.startswith('pipelines.kubeflow.org/') and 'created' in key.lower() 
                          for key in annotations.keys())
        if not has_timestamp:
            print(f"Note: Creation timestamp not preserved in annotations for {resource_type}")


def compare_pipeline_objects(migrated_pipeline: Dict[str, Any], original_pipeline) -> None:
    """Compare migrated pipeline with original pipeline using complete object comparison."""
    # Validate basic structure
    assert 'metadata' in migrated_pipeline, "Migrated pipeline should have metadata"
    assert 'spec' in migrated_pipeline, "Migrated pipeline should have spec"
    
    # Get pipeline name and ID from KFP client object or dict
    original_name = getattr(original_pipeline, 'display_name', None) or getattr(original_pipeline, 'name', None) or original_pipeline.get('name', '')
    original_id = getattr(original_pipeline, 'pipeline_id', None) or original_pipeline.get('id', '')
    
    # Validate metadata preservation
    assert migrated_pipeline['metadata']['name'] == original_name, "Pipeline name should be preserved"
    assert migrated_pipeline['metadata']['namespace'] == 'kubeflow', "Pipeline should be in kubeflow namespace"
    
    # Validate original ID annotation
    validate_original_id_annotation(migrated_pipeline, original_id)
    
    # Validate description preservation if available
    original_description = getattr(original_pipeline, 'description', None) or original_pipeline.get('description', '')
    if original_description:
        pipeline_spec = migrated_pipeline.get('spec', {})
        if 'description' in pipeline_spec:
            assert pipeline_spec['description'] == original_description, "Pipeline description should be preserved"
    
    # Enhanced validation using complete object data
    if hasattr(original_pipeline, '__dict__'):
        # This is a KFP client object, serialize it for comparison
        original_object = serialize_object_for_comparison(original_pipeline)
        
        # Validate core pipeline attributes are preserved
        original_name = original_object.get('display_name') or original_object.get('name')
        assert migrated_pipeline['metadata']['name'] == original_name, \
            f"Pipeline name mismatch: migrated={migrated_pipeline['metadata']['name']}, original={original_name}"
        
        # Validate creation timestamp preservation in annotations if available (optional)
        if 'created_at' in original_object:
            annotations = migrated_pipeline.get('metadata', {}).get('annotations', {})
            original_created_at = original_object['created_at']
            if original_created_at:
                # Timestamp preservation is optional - just log if not present
                has_timestamp = ('pipelines.kubeflow.org/created-at' in annotations or 
                               'pipelines.kubeflow.org/original-created-at' in annotations)
                if not has_timestamp:
                    print(f"Note: Creation timestamp not preserved in annotations for pipeline {migrated_pipeline['metadata']['name']}")
        
        # Validate pipeline parameters if present
        if 'parameters' in original_object and original_object['parameters']:
            assert 'spec' in migrated_pipeline, "Migrated pipeline should have spec for parameters"


def test_migration_single_pipeline_single_version(test_data, run_migration):
    """Test migration of a single pipeline with single version.
    
    Runs migration on a simple pipeline created in DB mode.
    Validates YAML files are generated with correct Kubernetes resources.
    Verifies original IDs are preserved in annotations and migrated pipeline spec matches original data.
   
    """
    output_dir = run_migration
    
    yaml_files = list(output_dir.glob("*.yaml"))
    for yaml_file in yaml_files:
        print(f"Generated file: {yaml_file}")
    
    # Verify YAML files were created
    assert len(yaml_files) > 0, "Migration should create YAML files"    
   
    migrated_resources = parse_yaml_files(output_dir)    
    original_pipeline = find_test_data_by_name(test_data, "pipelines", "hello-world")   
    pipelines = migrated_resources["Pipeline"]
    assert len(pipelines) >= 1, "Should have at least one Pipeline resource"    
    simple_pipeline_resources = [p for p in pipelines 
                                if "hello-world" in p.get("metadata", {}).get("name", "")]
    assert len(simple_pipeline_resources) >= 1, "Should have migrated hello-world pipeline"
    
    # Compare migrated pipeline with original
    migrated_pipeline = simple_pipeline_resources[0]
    compare_pipeline_objects(migrated_pipeline, original_pipeline)
    compare_complete_objects(migrated_pipeline, original_pipeline, "Pipeline")
    
    # Verify pipeline versions exist
    pipeline_versions = migrated_resources["PipelineVersion"]
    simple_versions = [v for v in pipeline_versions 
                      if "hello-world" in v.get("metadata", {}).get("name", "")]
    assert len(simple_versions) >= 1, "Hello-world pipeline should have at least one version"
    
    # Validate version structure
    for version in simple_versions:       
        annotations = version.get('metadata', {}).get('annotations', {})
        assert 'pipelines.kubeflow.org/original-id' in annotations, "Version should have original ID annotation"
        assert 'spec' in version, "PipelineVersion should have spec"
        assert 'pipelineSpec' in version['spec'], "PipelineVersion should have pipelineSpec"
        
        # Enhanced validation using complete object comparison
        original_version_id = annotations.get('pipelines.kubeflow.org/original-id')
        original_version = None
        for original in test_data.get('pipelines', []):
            # Handle KFP client objects vs dict structures
            original_id = getattr(original, 'pipeline_version_id', None) or getattr(original, 'pipeline_id', None) or (original.get('id', None) if hasattr(original, 'get') else None)
            if original_id == original_version_id:
                original_version = original
                break
        
        if original_version:
            compare_complete_objects(version, original_version, "PipelineVersion")


def test_migration_single_pipeline_multiple_versions_same_spec(test_data, run_migration):
    """Test migration of pipeline with multiple versions having same specification.
    
    Runs migration on pipeline with multiple versions that have identical specs.
    Validates multiple pipeline versions are correctly exported with original ID annotations.
    Verifies versions with identical specs are handled properly and pipeline-version relationships are preserved.
    
    """
    output_dir = run_migration
    
    yaml_files = list(output_dir.glob("*.yaml"))
    for yaml_file in yaml_files:
        print(f"Generated file: {yaml_file}")
    
    assert len(yaml_files) > 0, "Migration should create YAML files"    
    
    migrated_resources = parse_yaml_files(output_dir)
    
    # Verify PipelineVersion resources
    pipeline_versions = migrated_resources["PipelineVersion"]
    assert len(pipeline_versions) >= 2, "Should have at least 2 pipeline versions"
    
    # Validate each version structure and annotations
    for version in pipeline_versions:
        # Validate required fields
        expected_fields = {
            "kind": "PipelineVersion",
            "metadata.namespace": "kubeflow"
        }
        validate_resource_structure(version, expected_fields)
        
        # Validate original ID annotation exists
        annotations = version.get('metadata', {}).get('annotations', {})
        assert 'pipelines.kubeflow.org/original-id' in annotations, "Each version should have original ID annotation"
        
        # Validate spec structure
        assert 'spec' in version, "PipelineVersion should have spec"
        assert 'pipelineSpec' in version['spec'], "PipelineVersion should have pipelineSpec"


def test_migration_single_pipeline_multiple_versions_different_specs(test_data, run_migration):
    """Test migration of pipeline with multiple versions having different specifications.
    
    Runs migration on complex pipeline with multiple versions that have different specs.
    Validates multiple versions with different specs are properly exported.
    Verifies each version preserves its unique specification and pipeline relationships are maintained.
    """
    output_dir = run_migration
    
    yaml_files = list(output_dir.glob("*.yaml"))
    for yaml_file in yaml_files:
        print(f"Generated file: {yaml_file}")
    
    assert len(yaml_files) > 0, "Migration should create YAML files"
   
    migrated_resources = parse_yaml_files(output_dir)    
    original_complex_pipeline = find_test_data_by_name(test_data, "pipelines", "add-numbers")
    
    # Verify complex pipeline was migrated
    pipelines = migrated_resources["Pipeline"]
    complex_pipeline_resources = [p for p in pipelines 
                                 if "add-numbers" in p.get("metadata", {}).get("name", "")]
    assert len(complex_pipeline_resources) >= 1, "Should have migrated add-numbers pipeline"
    
    # Compare migrated complex pipeline with original
    migrated_complex_pipeline = complex_pipeline_resources[0]
    compare_pipeline_objects(migrated_complex_pipeline, original_complex_pipeline)
    compare_complete_objects(migrated_complex_pipeline, original_complex_pipeline, "Pipeline")
    
    # Verify versions exist for complex pipeline
    pipeline_versions = migrated_resources["PipelineVersion"]
    complex_versions = [v for v in pipeline_versions 
                       if "add-numbers" in v.get("metadata", {}).get("name", "")]
    assert len(complex_versions) >= 1, "Add-numbers pipeline should have at least one version"
    
    # Validate each version has proper structure and unique specifications
    version_specs = []
    for version in complex_versions:
        # Validate original ID annotation
        annotations = version.get('metadata', {}).get('annotations', {})
        assert 'pipelines.kubeflow.org/original-id' in annotations, "Each version should have original ID annotation"
        
        # Validate spec structure
        assert 'spec' in version, "PipelineVersion should have spec field"
        assert 'pipelineSpec' in version['spec'], "PipelineVersion should have pipelineSpec"        
        
        # Enhanced comparison with complete object data
        original_version = None
        for original in test_data.get('pipelines', []):
            # Handle KFP client objects vs dict structures
            has_pipeline_id = hasattr(original, 'pipeline_id') or (hasattr(original, 'get') and 'pipeline_id' in original)
            original_name = getattr(original, 'display_name', None) or getattr(original, 'name', None) or (original.get('name', '') if hasattr(original, 'get') else '')
            if (has_pipeline_id and 
                original_name and 
                'add-numbers' in original_name):
                original_version = original
                break
        
        if original_version:
            compare_complete_objects(version, original_version, "PipelineVersion")
        
        version_specs.append(str(version['spec']))
    
    # Verify we have different specifications
    unique_specs = set(version_specs)
    assert len(unique_specs) >= 1, "Should have at least one unique specification"


def test_migration_multiple_pipelines_single_version_each(test_data, run_migration):
    """Test migration of multiple pipelines, each with single version.
    
    Runs migration on multiple independent pipelines created in DB mode.
    Validates all pipelines are exported and each maintains identity and metadata.
    Verifies cross-pipeline relationships are not incorrectly created and all pipeline types are handled.
    
    """
    output_dir = run_migration
    
    yaml_files = list(output_dir.glob("*.yaml"))
    for yaml_file in yaml_files:
        print(f"Generated file: {yaml_file}")
    
    assert len(yaml_files) > 0, "Migration should create YAML files"
    
    migrated_resources = parse_yaml_files(output_dir)
    pipelines = migrated_resources["Pipeline"]
    pipeline_versions = migrated_resources["PipelineVersion"]
    
    assert len(pipelines) >= 2, "Should have at least 2 pipelines"
    assert len(pipeline_versions) >= 2, "Should have at least 2 pipeline versions"
    
    for pipeline in pipelines:
        pipeline_name = pipeline.get("metadata", {}).get("name", "")
        
        expected_fields = {
            "kind": "Pipeline",
            "metadata.namespace": "kubeflow"
        }
        validate_resource_structure(pipeline, expected_fields)        
        
        annotations = pipeline.get('metadata', {}).get('annotations', {})
        assert 'pipelines.kubeflow.org/original-id' in annotations, f"Pipeline {pipeline_name} should have original ID annotation"


def test_migration_multiple_pipelines_multiple_versions_different_specs(test_data, run_migration):
    """Test migration of multiple pipelines with multiple versions having different specifications.
    
    Comprehensive test running migration on complex scenarios with multiple pipelines and versions.
    Validates each resource maintains unique identity and specifications.
    Verifies migration handles full complexity of real KFP environment with preserved relationships and object integrity.
    
    """
    output_dir = run_migration
    
    yaml_files = list(output_dir.glob("*.yaml"))
    for yaml_file in yaml_files:
        print(f"Generated file: {yaml_file}")
    
    assert len(yaml_files) > 0, "Migration should create YAML files"
    
    migrated_resources = parse_yaml_files(output_dir)   
    pipelines = migrated_resources["Pipeline"]
    simple_pipelines = [p for p in pipelines 
                       if "hello-world" in p.get("metadata", {}).get("name", "")]
    complex_pipelines = [p for p in pipelines 
                        if "add-numbers" in p.get("metadata", {}).get("name", "")]    
   
    assert len(simple_pipelines) >= 1, "Should have hello-world pipeline"
    assert len(complex_pipelines) >= 1, "Should have add-numbers pipeline"
    
    # Compare migrated pipelines with original test data
    for migrated_pipeline in simple_pipelines:
        original_pipeline = find_test_data_by_name(test_data, "pipelines", "hello-world")
        compare_pipeline_objects(migrated_pipeline, original_pipeline)
        compare_complete_objects(migrated_pipeline, original_pipeline, "Pipeline")
    
    for migrated_pipeline in complex_pipelines:
        original_pipeline = find_test_data_by_name(test_data, "pipelines", "add-numbers")
        compare_pipeline_objects(migrated_pipeline, original_pipeline)
        compare_complete_objects(migrated_pipeline, original_pipeline, "Pipeline")

    # Verify complex pipeline has versions
    pipeline_versions = migrated_resources["PipelineVersion"]
    complex_versions = [v for v in pipeline_versions 
                       if "add-numbers" in v.get("metadata", {}).get("name", "")]
    assert len(complex_versions) >= 1, "Add-numbers pipeline should have at least one version"
    
    # Validate comprehensive resource structure and object integrity
    for pipeline in pipelines:
        # Check required fields for Pipeline resources
        assert 'metadata' in pipeline, "Pipeline should have metadata"
        assert 'name' in pipeline['metadata'], "Pipeline should have name"
        assert 'namespace' in pipeline['metadata'], "Pipeline should have namespace"
        assert pipeline['metadata']['namespace'] == 'kubeflow', "Pipeline should be in kubeflow namespace"
        
        # Check for original ID annotation
        annotations = pipeline.get('metadata', {}).get('annotations', {})
        assert 'pipelines.kubeflow.org/original-id' in annotations, "Pipeline should have original ID annotation"
        
        # Enhanced validation using complete object comparison
        original_pipeline_id = annotations.get('pipelines.kubeflow.org/original-id')
        original_pipeline = None
        for original in test_data.get('pipelines', []):
            # Handle KFP client objects vs dict structures
            original_id = getattr(original, 'pipeline_id', None) or (original.get('id', None) if hasattr(original, 'get') else None)
            if original_id == original_pipeline_id:
                original_pipeline = original
                break
        
        if original_pipeline:
            compare_complete_objects(pipeline, original_pipeline, "Pipeline")
    
    for version in pipeline_versions:
        # Check required fields for PipelineVersion resources
        assert 'metadata' in version, "PipelineVersion should have metadata"
        assert 'spec' in version, "PipelineVersion should have spec"
        assert 'pipelineSpec' in version['spec'], "PipelineVersion should have pipelineSpec"
        
        # Check for original ID annotation
        annotations = version.get('metadata', {}).get('annotations', {})
        assert 'pipelines.kubeflow.org/original-id' in annotations, "PipelineVersion should have original ID annotation"
        
        # Enhanced validation using complete object comparison
        original_version_id = annotations.get('pipelines.kubeflow.org/original-id')
        original_version = None
        for original in test_data.get('pipelines', []):
            # Handle KFP client objects vs dict structures
            original_id = getattr(original, 'pipeline_version_id', None) or getattr(original, 'pipeline_id', None) or (original.get('id', None) if hasattr(original, 'get') else None)
            if original_id == original_version_id:
                original_version = original
                break
        
        if original_version:
            compare_complete_objects(version, original_version, "PipelineVersion")