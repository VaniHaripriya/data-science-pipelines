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
import kfp.dsl as dsl

# Environment variables
KFP_ENDPOINT = os.environ.get('KFP_ENDPOINT', 'http://localhost:8888')
KFP_UI_ENDPOINT = os.environ.get('KFP_UI_ENDPOINT', 'http://localhost:8080')
KFP_NAMESPACE = os.environ.get('KFP_NAMESPACE', 'kubeflow')

# Define pipeline functions using KFP DSL
@dsl.component
def print_hello(message: str):
    """Simple component that prints a message."""
    print(f"Hello: {message}")

@dsl.component
def data_preprocessing(input_data: str):
    """Component for data preprocessing."""
    print(f"Processing data: {input_data}")

@dsl.component
def model_training(input_data: str):
    """Component for model training."""
    print(f"Training model with input: {input_data}")

@dsl.component
def model_evaluation(input_data: str):
    """Component for model evaluation."""
    print(f"Evaluating model with input: {input_data}")

@dsl.pipeline(name="simple-pipeline")
def simple_pipeline(message: str = "Hello World"):
    """A simple test pipeline."""
    print_hello(message=message)

@dsl.pipeline(name="complex-pipeline")
def complex_pipeline(input_data: str = "test_data"):
    """A complex test pipeline with multiple components."""
    preprocessing_task = data_preprocessing(input_data=input_data)
    training_task = model_training(input_data=input_data)
    training_task.after(preprocessing_task)

@dsl.pipeline(name="complex-pipeline-v2")
def complex_pipeline_v2(input_data: str = "test_data"):
    """A complex test pipeline with multiple components including evaluation."""
    preprocessing_task = data_preprocessing(input_data=input_data)
    training_task = model_training(input_data=input_data)
    evaluation_task = model_evaluation(input_data=input_data)
    training_task.after(preprocessing_task)
    evaluation_task.after(training_task)

def create_pipeline(name, description, pipeline_func):
    """Create a pipeline in KFP Database mode."""
    try:
        client = kfp.Client(host=KFP_ENDPOINT)
        
        # Upload pipeline using KFP client from pipeline function
        pipeline = client.upload_pipeline_from_pipeline_func(
            pipeline_func=pipeline_func,
            pipeline_name=name,
            description=description
        )
        
        return {
            "id": pipeline.pipeline_id,
            "name": pipeline.display_name,
            "description": description
        }
    except Exception as e:
        print(f"Failed to create pipeline {name}: {e}")
        return None

def create_pipeline_version(pipeline_id, name, pipeline_func):
    """Create a pipeline version in KFP Database mode."""
    try:
        client = kfp.Client(host=KFP_ENDPOINT)
        
        # Upload pipeline version using KFP client from pipeline function
        version = client.upload_pipeline_version_from_pipeline_func(
            pipeline_func=pipeline_func,
            pipeline_version_name=name,
            pipeline_id=pipeline_id
        )
        
        return {
            "id": version.pipeline_version_id,
            "name": version.display_name,
            "pipeline_id": pipeline_id
        }
    except Exception as e:
        print(f"Failed to create pipeline version {name}: {e}")
        return None

def create_experiment(name, description):
    """Create an experiment in KFP Database mode."""
    try:
        client = kfp.Client(host=KFP_ENDPOINT)
        
        # Create experiment using KFP client
        experiment = client.create_experiment(
            name=name,
            description=description
        )
        
        return {
            "id": experiment.experiment_id,
            "name": experiment.display_name,
            "description": description
        }
    except Exception as e:
        print(f"Failed to create experiment {name}: {e}")
        return None

def create_run(experiment_id, pipeline_id, pipeline_version_id, name, parameters=None):
    """Create a pipeline run in KFP Database mode."""
    try:
        client = kfp.Client(host=KFP_ENDPOINT)
        
        # Create run using the KFP client's internal API
        import kfp_server_api
        
        # Create the run body using the proper API model
        run_body = kfp_server_api.V1Run(
            name=name,
            pipeline_spec=kfp_server_api.V1PipelineSpec(
                parameters=parameters or []
            ),
            resource_references=[
                kfp_server_api.V1ResourceReference(
                    key=kfp_server_api.V1ResourceKey(
                        id=pipeline_version_id,
                        type=kfp_server_api.V1ResourceType.PIPELINE_VERSION
                    ),
                    relationship=kfp_server_api.V1Relationship.OWNER
                ),
                kfp_server_api.V1ResourceReference(
                    key=kfp_server_api.V1ResourceKey(
                        id=experiment_id,
                        type=kfp_server_api.V1ResourceType.EXPERIMENT
                    ),
                    relationship=kfp_server_api.V1Relationship.OWNER
                )
            ]
        )
        
        # Use the client's internal run API
        run_data = client._run_api.run_service_create_run(run=run_body)
        
        return {
            "id": run_data.run_id,
            "name": run_data.name or name,
            "pipeline_spec": {
                "pipeline_id": pipeline_id,
                "pipeline_version_id": pipeline_version_id
            },
            "resource_references": [
                {
                    "key": {
                        "type": "EXPERIMENT",
                        "id": experiment_id
                    },
                    "relationship": "OWNER"
                }
            ],
            "parameters": parameters
        }
    except Exception as e:
        print(f"Failed to create run {name}: {e}")
        return None

def create_recurring_run(experiment_id, pipeline_id, pipeline_version_id, name, cron_expression, parameters=None):
    """Create a recurring run in KFP Database mode."""
    try:
        client = kfp.Client(host=KFP_ENDPOINT)
        
        # Create recurring run using the KFP client's internal API
        import kfp_server_api
        
        # Create the recurring run body using the proper API model
        recurring_run_body = kfp_server_api.V1Job(
            name=name,
            pipeline_spec=kfp_server_api.V1PipelineSpec(
                pipeline_id=pipeline_id,
                pipeline_version_id=pipeline_version_id,
                parameters=parameters or []
            ),
            resource_references=[
                kfp_server_api.V1ResourceReference(
                    key=kfp_server_api.V1ResourceKey(
                        id=experiment_id,
                        type=kfp_server_api.V1ResourceType.EXPERIMENT
                    ),
                    relationship=kfp_server_api.V1Relationship.OWNER
                )
            ],
            trigger=kfp_server_api.V1Trigger(
                cron_schedule=kfp_server_api.V1CronSchedule(
                    cron=cron_expression
                )
            )
        )
        
        # Use the client's internal job API
        recurring_run_data = client._job_api.run_service_create_job(job=recurring_run_body)
        
        return {
            "id": recurring_run_data.id,
            "name": recurring_run_data.name or name,
            "pipeline_spec": {
                "pipeline_id": pipeline_id,
                "pipeline_version_id": pipeline_version_id
            },
            "resource_references": [
                {
                    "key": {
                        "type": "EXPERIMENT",
                        "id": experiment_id
                    },
                    "relationship": "OWNER"
                }
            ],
            "trigger": {
                "cron_schedule": {
                    "cron": cron_expression
                }
            },
            "parameters": parameters
        }
    except Exception as e:
        print(f"Failed to create recurring run {name}: {e}")
        return None



def main():   
    print("Setting up test environment for KFP migration tests...")    
   
    test_data = {
        "pipelines": [],
        "experiments": [],
        "runs": [],
        "recurring_runs": []
    }
    
    # Create simple pipeline
    pipeline1 = create_pipeline("simple-pipeline", "A simple test pipeline", simple_pipeline)
    if pipeline1:
        test_data["pipelines"].append(pipeline1)
        print(f"Created pipeline: {pipeline1['name']} (ID: {pipeline1['id']})")
        
        # Create pipeline version
        version1 = create_pipeline_version(pipeline1["id"], "v1", simple_pipeline)
        if version1:
            test_data["pipelines"].append(version1)
            print(f"Created pipeline version: {version1['name']} (ID: {version1['id']})")
    
    # Create pipeline with multiple versions and different specs
    pipeline2 = create_pipeline("complex-pipeline", "A complex test pipeline", complex_pipeline)
    if pipeline2:
        test_data["pipelines"].append(pipeline2)
        print(f"Created pipeline: {pipeline2['name']} (ID: {pipeline2['id']})")
        
        # Create two versions with different specs
        version2_1 = create_pipeline_version(pipeline2["id"], "v1", complex_pipeline)
        if version2_1:
            test_data["pipelines"].append(version2_1)
            print(f"Created pipeline version: {version2_1['name']} (ID: {version2_1['id']})")
        
        version2_2 = create_pipeline_version(pipeline2["id"], "v2", complex_pipeline_v2)
        if version2_2:
            test_data["pipelines"].append(version2_2)
            print(f"Created pipeline version: {version2_2['name']} (ID: {version2_2['id']})")
    
    # Create experiment
    experiment = create_experiment("migration-test-experiment", "Test experiment for migration")
    if experiment:
        test_data["experiments"].append(experiment)
        print(f"Created experiment: {experiment['name']} (ID: {experiment['id']})")
        
        # Create a run in the experiment
        if pipeline1 and version1:
            run = create_run(
                experiment["id"],
                pipeline1["id"],
                version1["id"],
                "test-run",
                parameters=[{"name": "param1", "value": "value1"}]
            )
            if run:
                test_data["runs"].append(run)
                print(f"Created run: {run['name']} (ID: {run['id']})")
        
        # Create a recurring run in the experiment
        if pipeline2 and version2_1:
            recurring_run = create_recurring_run(
                experiment["id"],
                pipeline2["id"],
                version2_1["id"],
                "test-recurring-run",
                "0 0 * * *",  # Daily at midnight
                parameters=[{"name": "param1", "value": "value1"}]
            )
            if recurring_run:
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

