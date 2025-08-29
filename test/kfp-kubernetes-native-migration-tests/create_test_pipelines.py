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
import pickle
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

    print(f"Complete Pipeline Object: {complete_pipeline}")
    print(f"Pipeline Object Serialized: {serialize_object_for_comparison(complete_pipeline)}")
    
    # Return the complete pipeline object directly for comprehensive comparison
    return complete_pipeline

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
    complete_version = client.get_pipeline_version(pipeline_id, version.pipeline_version_id)

    print(f"Complete Version Object: {complete_version}")
    print(f"Version Object Serialized: {serialize_object_for_comparison(complete_version)}")
    
    # Return the complete pipeline version object directly for comprehensive comparison
    return complete_version

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

    print(f"Complete Experiment Object: {complete_experiment}")
    print(f"Experiment Object Serialized: {serialize_object_for_comparison(complete_experiment)}")
    
    # Return the complete experiment object directly for comprehensive comparison
    return complete_experiment

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

    print(f"Complete Run Object: {complete_run}")
    print(f"Run Object Serialized: {serialize_object_for_comparison(complete_run)}")
    
    # Return the complete run object directly for comprehensive comparison
    return complete_run

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

    print(f"Complete Recurring Run Object: {complete_recurring_run}")
    print(f"Recurring Run Object Serialized: {serialize_object_for_comparison(complete_recurring_run)}")
    
    # Return the complete recurring run object directly for comprehensive comparison
    return complete_recurring_run

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
    # Store the complete pipeline object directly
    test_data["pipelines"].append(pipeline1)
    print(f"Created pipeline: {pipeline1.display_name} (ID: {pipeline1.pipeline_id})")

    # Create a version for the first pipeline
    version1 = create_pipeline_version(
        pipeline1.pipeline_id, 
        "v1", 
        pipeline1_config["path"]
    )
    # Store the complete version object directly
    test_data["pipelines"].append(version1)
    print(f"Created pipeline version: {version1.display_name} (ID: {version1.pipeline_version_id})")

    # Create second pipeline from file
    pipeline2_config = PIPELINE_FILES[1]  # add-numbers
    pipeline2 = create_pipeline(
        pipeline2_config["name"], 
        pipeline2_config["description"], 
        pipeline2_config["path"]
    )
    # Store the complete pipeline object directly
    test_data["pipelines"].append(pipeline2)
    print(f"Created pipeline: {pipeline2.display_name} (ID: {pipeline2.pipeline_id})")

    # Create a version for the second pipeline 
    version2 = create_pipeline_version(
        pipeline2.pipeline_id, 
        "v1", 
        pipeline2_config["path"]
    )
    # Store the complete version object directly
    test_data["pipelines"].append(version2)
    print(f"Created pipeline version: {version2.display_name} (ID: {version2.pipeline_version_id})")

    # Create experiment
    experiment = create_experiment("migration-test-experiment", "Test experiment for migration")
    # Store the complete experiment object directly
    test_data["experiments"].append(experiment)
    print(f"Created experiment: {experiment.display_name} (ID: {experiment.experiment_id})")

    # Create a run with the hello-world pipeline
    run = create_run(
        experiment.experiment_id,
        pipeline1.pipeline_id,
        version1.pipeline_version_id,
        "test-hello-world-run",
        parameters=None
    )
    # Store the complete run object directly
    test_data["runs"].append(run)
    print(f"Created run: {run.display_name} (ID: {run.run_id})")

    # Create a recurring run with the add-numbers pipeline
    recurring_run = create_recurring_run(
        experiment.experiment_id,
        pipeline2.pipeline_id,
        version2.pipeline_version_id,
        "test-add-numbers-recurring-run",
        "0 0 * * *",  
        parameters=[{"name": "a", "value": 5}, {"name": "b", "value": 3}]
    )
    # Store the complete recurring run object directly
    test_data["recurring_runs"].append(recurring_run)
    print(f"Created recurring run: {recurring_run.display_name} (ID: {recurring_run.recurring_run_id})")

    # Save test data for later use (using pickle for KFP objects)
    migration_test_data_file = Path("migration_test_data.pkl")
    with open(migration_test_data_file, "wb") as f:
        pickle.dump(test_data, f)
    
    # Also save a JSON version with serialized data for debugging
    migration_test_data_json = Path("migration_test_data.json")
    json_data = {
        "pipelines": [serialize_object_for_comparison(obj) for obj in test_data["pipelines"]],
        "experiments": [serialize_object_for_comparison(obj) for obj in test_data["experiments"]],
        "runs": [serialize_object_for_comparison(obj) for obj in test_data["runs"]],
        "recurring_runs": [serialize_object_for_comparison(obj) for obj in test_data["recurring_runs"]]
    }
    with open(migration_test_data_json, "w") as f:
        json.dump(json_data, f, indent=2, default=str)

    print(f"\nTest data saved to {migration_test_data_file}")
    print("Test environment setup complete!")    

    print(f"\nCreated:")
    # Count pipelines (have pipeline_id but not pipeline_version_id)
    pipelines = [p for p in test_data['pipelines'] if hasattr(p, 'pipeline_id') and not hasattr(p, 'pipeline_version_id')]
    # Count pipeline versions (have both pipeline_id and pipeline_version_id)
    versions = [p for p in test_data['pipelines'] if hasattr(p, 'pipeline_version_id')]
    print(f"- {len(pipelines)} pipelines")
    print(f"- {len(versions)} pipeline versions")
    print(f"- {len(test_data['experiments'])} experiments")
    print(f"- {len(test_data['runs'])} runs")
    print(f"- {len(test_data['recurring_runs'])} recurring runs")

if __name__ == "__main__":
    main()