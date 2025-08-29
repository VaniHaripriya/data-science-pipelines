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
import time
import requests
import subprocess
import sys
import os
from pathlib import Path
import kfp
from kfp.client import Client


KFP_ENDPOINT = os.environ.get('KFP_ENDPOINT', 'http://localhost:8888')

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

# Pipeline files to use for testing
PIPELINE_FILES = [
    {
        "name": "hello-world", 
        "path": "test_data/pipeline_files/valid/critical/hello-world.yaml",
        "description": "Simple hello world pipeline for migration testing"
    },
    {
        "name": "add-numbers",
        "path": "test_data/pipeline_files/valid/add_numbers.yaml", 
        "description": "Simple arithmetic pipeline with parameters for migration testing"
    }
]

def create_pipeline(name, description, pipeline_file_path):
    """Create a pipeline in KFP Database mode from YAML file."""
    client = Client(host=KFP_ENDPOINT)

    # Upload the pipeline
    pipeline = client.upload_pipeline(
        pipeline_package_path=pipeline_file_path,
        pipeline_name=name,
        description=description
    )

    # Retrieve the complete pipeline object from the database
    complete_pipeline = client.get_pipeline(pipeline.pipeline_id)

    # Return the complete pipeline object for comprehensive comparison
    pipeline_data = {
        "object": complete_pipeline,
        "object_serialized": serialize_object_for_comparison(complete_pipeline),
        "id": complete_pipeline.pipeline_id,
        "name": complete_pipeline.display_name,
        "description": getattr(complete_pipeline, 'description', description),
        "created_at": getattr(complete_pipeline, 'created_at', None),
        "parameters": getattr(complete_pipeline, 'parameters', None),
        "default_version": getattr(complete_pipeline, 'default_version', None),
        "url": getattr(complete_pipeline, 'url', None)
    }
    
    print(f"Complete Pipeline Object: {pipeline_data}")
    return pipeline_data

def create_pipeline_version(pipeline_id, name, pipeline_file_path):
    """Create a pipeline version in KFP Database mode from YAML file."""
    client = Client(host=KFP_ENDPOINT)

    # Upload the pipeline version
    version = client.upload_pipeline_version(
        pipeline_package_path=pipeline_file_path,
        pipeline_version_name=name,
        pipeline_id=pipeline_id
    )

    # Retrieve the complete pipeline version object from the database
    complete_version = client.get_pipeline_version(version.pipeline_version_id, pipeline_id)

    # Return the complete pipeline version object for comprehensive comparison
    version_data = {
        "object": complete_version,
        "object_serialized": serialize_object_for_comparison(complete_version),
        "id": complete_version.pipeline_version_id,
        "name": complete_version.display_name,
        "pipeline_id": pipeline_id,
        "created_at": getattr(complete_version, 'created_at', None),
        "parameters": getattr(complete_version, 'parameters', None),
        "description": getattr(complete_version, 'description', None),
        "package_url": getattr(complete_version, 'package_url', None),
        "pipeline_spec": getattr(complete_version, 'pipeline_spec', None)
    }
    
    print(f"Complete Version Object: {version_data}")
    return version_data

def create_experiment(name, description):
    """Create an experiment in KFP Database mode."""
    client = Client(host=KFP_ENDPOINT)

    # Create experiment using KFP client
    experiment = client.create_experiment(
        name=name,
        description=description
    )
    experiment_id = getattr(experiment, 'experiment_id', None)

    # Retrieve the complete experiment object from the database
    complete_experiment = client.get_experiment(experiment_id)

    # Return the complete experiment object for comprehensive comparison
    experiment_data = {
        "object": complete_experiment,
        "object_serialized": serialize_object_for_comparison(complete_experiment),
        "id": experiment_id,
        "name": getattr(complete_experiment, 'display_name', None),
        "description": getattr(complete_experiment, 'description', description),
        "created_at": getattr(complete_experiment, 'created_at', None),
        "storage_state": getattr(complete_experiment, 'storage_state', None),
        "namespace": getattr(complete_experiment, 'namespace', None)
    }
    
    print(f"Complete Experiment Object: {experiment_data}")
    return experiment_data

def create_run(experiment_id, pipeline_id, pipeline_version_id, name, parameters=None):
    """Create a pipeline run in KFP Database mode."""
    client = Client(host=KFP_ENDPOINT)
    run_params = {}
    if parameters:
        for param in parameters:
            if isinstance(param, dict) and "name" in param and "value" in param:
                run_params[param["name"]] = param["value"]       

    # Create the run
    run_data = client.run_pipeline(
        experiment_id=experiment_id,
        job_name=name,
        pipeline_id=pipeline_id,
        version_id=pipeline_version_id,
        params=run_params
    )
    run_id = getattr(run_data, 'run_id', None)

    # Retrieve the complete run object from the database
    complete_run = client.get_run(run_id)

    # Return the complete run object for comprehensive comparison
    run_data = {
        "object": complete_run,
        "object_serialized": serialize_object_for_comparison(complete_run),
        "id": run_id,
        "name": getattr(complete_run, 'display_name', None),
        "pipeline_spec": {
            "pipeline_id": pipeline_id,
            "pipeline_version_id": pipeline_version_id
        },
        "resource_references": getattr(complete_run, 'resource_references', []),
        "parameters": parameters,
        "created_at": getattr(complete_run, 'created_at', None),
        "finished_at": getattr(complete_run, 'finished_at', None),
        "status": getattr(complete_run, 'status', None),
        "error": getattr(complete_run, 'error', None),
        "metrics": getattr(complete_run, 'metrics', None),
        "workflow_manifest": getattr(complete_run, 'workflow_manifest', None)
    }
    
    print(f"Complete Run Object: {run_data}")
    return run_data

def create_recurring_run(experiment_id, pipeline_id, pipeline_version_id, name, cron_expression, parameters=None):
    """Create a recurring run in KFP Database mode."""
    client = Client(host=KFP_ENDPOINT)
    run_params = {}
    if parameters:
        for param in parameters:
            if isinstance(param, dict) and "name" in param and "value" in param:
                run_params[param["name"]] = param["value"]

    # Create the recurring run
    recurring_run_data = client.create_recurring_run(
        experiment_id=experiment_id,
        job_name=name,
        pipeline_id=pipeline_id,
        version_id=pipeline_version_id,
        cron_expression=cron_expression,
        params=run_params
    )       
    recurring_run_id = getattr(recurring_run_data, 'recurring_run_id', None)

    # Retrieve the complete recurring run object from the database
    complete_recurring_run = client.get_recurring_run(recurring_run_id)

    # Return the complete recurring run object for comprehensive comparison
    recurring_run_data = {
        "object": complete_recurring_run,
        "object_serialized": serialize_object_for_comparison(complete_recurring_run),
        "id": recurring_run_id,
        "name": getattr(complete_recurring_run, 'display_name', None),
        "pipeline_spec": {
            "pipeline_id": pipeline_id,
            "pipeline_version_id": pipeline_version_id
        },
        "resource_references": getattr(complete_recurring_run, 'resource_references', []),
        "trigger": getattr(complete_recurring_run, 'trigger', {}),
        "parameters": parameters,
        "created_at": getattr(complete_recurring_run, 'created_at', None),
        "updated_at": getattr(complete_recurring_run, 'updated_at', None),
        "status": getattr(complete_recurring_run, 'status', None),
        "error": getattr(complete_recurring_run, 'error', None),
        "enabled": getattr(complete_recurring_run, 'enabled', None),
        "max_concurrency": getattr(complete_recurring_run, 'max_concurrency', None),
        "no_catchup": getattr(complete_recurring_run, 'no_catchup', None)
    }
    
    print(f"Complete Recurring Run Object: {recurring_run_data}")
    return recurring_run_data

def main():   
    print("Setting up test environment for KFP migration tests using existing pipeline files...")    

    test_data = {
        "pipelines": [],
        "experiments": [],
        "runs": [],
        "recurring_runs": []
    }

    # Verify pipeline files exist
    for pipeline_file in PIPELINE_FILES:
        file_path = Path(pipeline_file["path"])
        if not file_path.exists():
            print(f"Error: Pipeline file not found: {file_path}")
            sys.exit(1)
        print(f"Found pipeline file: {file_path}")

    # Create pipelines from existing YAML files
    pipeline1_config = PIPELINE_FILES[0]  # hello-world
    pipeline1 = create_pipeline(
        pipeline1_config["name"], 
        pipeline1_config["description"], 
        pipeline1_config["path"]
    )
    test_data["pipelines"].append(pipeline1)
    print(f"Created pipeline: {pipeline1['name']} (ID: {pipeline1['id']})")

    # Create a version for the first pipeline
    version1 = create_pipeline_version(
        pipeline1["id"], 
        "v1", 
        pipeline1_config["path"]
    )
    test_data["pipelines"].append(version1)
    print(f"Created pipeline version: {version1['name']} (ID: {version1['id']})")

    # Create second pipeline from file
    pipeline2_config = PIPELINE_FILES[1]  # add-numbers
    pipeline2 = create_pipeline(
        pipeline2_config["name"], 
        pipeline2_config["description"], 
        pipeline2_config["path"]
    )
    test_data["pipelines"].append(pipeline2)
    print(f"Created pipeline: {pipeline2['name']} (ID: {pipeline2['id']})")

    # Create a version for the second pipeline 
    version2 = create_pipeline_version(
        pipeline2["id"], 
        "v1", 
        pipeline2_config["path"]
    )
    test_data["pipelines"].append(version2)
    print(f"Created pipeline version: {version2['name']} (ID: {version2['id']})")

    # Create experiment
    experiment = create_experiment("migration-test-experiment", "Test experiment for migration")
    test_data["experiments"].append(experiment)
    print(f"Created experiment: {experiment['name']} (ID: {experiment['id']})")

    # Create a run with the hello-world pipeline
    run = create_run(
        experiment["id"],
        pipeline1["id"],
        version1["id"],
        "test-hello-world-run",
        parameters=None
    )
    test_data["runs"].append(run)
    print(f"Created run: {run['name']} (ID: {run['id']})")

    # Create a recurring run with the add-numbers pipeline
    recurring_run = create_recurring_run(
        experiment["id"],
        pipeline2["id"],
        version2["id"],
        "test-add-numbers-recurring-run",
        "0 0 * * *",  
        parameters=[{"name": "a", "value": "5"}, {"name": "b", "value": "3"}]
    )
    test_data["recurring_runs"].append(recurring_run)
    print(f"Created recurring run: {recurring_run['name']} (ID: {recurring_run['id']})")

    # Save test data for later use
    migration_test_data_file = Path("migration_test_data.json")
    with open(migration_test_data_file, "w") as f:
        json.dump(test_data, f, indent=2)

    print(f"\nTest data saved to {migration_test_data_file}")
    print("Test environment setup complete!")    

    print(f"\nCreated:")
    print(f"- {len([p for p in test_data['pipelines'] if 'pipeline_id' not in p])} pipelines")
    print(f"- {len([p for p in test_data['pipelines'] if 'pipeline_id' in p])} pipeline versions")
    print(f"- {len(test_data['experiments'])} experiments")
    print(f"- {len(test_data['runs'])} runs")
    print(f"- {len(test_data['recurring_runs'])} recurring runs")

if __name__ == "__main__":
    main()