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

# Environment variables
KFP_ENDPOINT = os.environ.get('KFP_ENDPOINT', 'http://localhost:8888')
KFP_UI_ENDPOINT = os.environ.get('KFP_UI_ENDPOINT', 'http://localhost:8080')
KFP_NAMESPACE = os.environ.get('KFP_NAMESPACE', 'kubeflow')

def create_pipeline(name, description, pipeline_spec):
    """Create a pipeline in KFP Database mode."""
    try:
        client = kfp.Client(host=KFP_ENDPOINT)
        
        # Create a temporary pipeline YAML file
        import tempfile
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(pipeline_spec, f)
            pipeline_file = f.name
        
        # Upload pipeline using KFP client
        pipeline = client.upload_pipeline(
            pipeline_package_path=pipeline_file,
            pipeline_name=name,
            description=description
        )
        
        # Clean up temporary file
        os.unlink(pipeline_file)
        
        return {
            "id": pipeline.pipeline_id,
            "name": pipeline.display_name,
            "description": description,
            "pipeline_spec": pipeline_spec
        }
    except Exception as e:
        print(f"Failed to create pipeline {name}: {e}")
        return None

def create_pipeline_version(pipeline_id, name, pipeline_spec):
    """Create a pipeline version in KFP Database mode."""
    try:
        client = kfp.Client(host=KFP_ENDPOINT)
        
        # Create a temporary pipeline YAML file
        import tempfile
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(pipeline_spec, f)
            pipeline_file = f.name
        
        # Upload pipeline version using KFP client
        version = client.upload_pipeline_version(
            pipeline_package_path=pipeline_file,
            pipeline_version_name=name,
            pipeline_id=pipeline_id
        )
        
        # Clean up temporary file
        os.unlink(pipeline_file)
        
        return {
            "id": version.pipeline_version_id,
            "name": version.display_name,
            "pipeline_id": pipeline_id,
            "pipeline_spec": pipeline_spec
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
        
        # Create run using the runs API directly (like in versioned pipeline examples)
        run_body = {
            "name": name,
            "pipeline_spec": {
                "parameters": parameters or []
            },
            "resource_references": [
                {"key": {"id": pipeline_version_id, "type": 4}, "relationship": 2},  # Pipeline version
                {"key": {"id": experiment_id, "type": 1}, "relationship": 1}  # Experiment
            ]
        }
        
        run = client.runs.create_run(run_body)
        
        return {
            "id": run.run_id,
            "name": run.display_name or name,
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
        
        # Create recurring run using KFP client
        recurring_run = client.create_recurring_run(
            experiment_id=experiment_id,
            job_name=name,
            pipeline_id=pipeline_id,
            version_id=pipeline_version_id,
            cron_expression=cron_expression,
            params=parameters  # Use 'params' not 'arguments'
        )
        
        return {
            "id": recurring_run.recurring_run_id,
            "name": recurring_run.display_name or name,
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
    simple_pipeline_spec = {
        "schemaVersion": "2.1.0",
        "sdkVersion": "kfp-2.0.0",
        "pipelineInfo": {
            "name": "simple-pipeline"
        },
        "components": {
            "comp-print-hello": {
                "executorLabel": "exec-print-hello",
                "inputDefinitions": {
                    "parameters": {
                        "message": {
                            "parameterType": "STRING"
                        }
                    }
                }
            }
        },
        "deploymentSpec": {
            "executors": {
                "exec-print-hello": {
                    "container": {
                        "image": "python:3.9",
                        "command": ["echo"],
                        "args": ["{{$.inputs.parameters['message']}}"]
                    }
                }
            }
        },
        "root": {
            "dag": {
                "tasks": {
                    "print-hello": {
                        "componentRef": {
                            "name": "comp-print-hello"
                        },
                        "inputs": {
                            "parameters": {
                                "message": {
                                    "componentInputParameter": "message"
                                }
                            }
                        },
                        "taskInfo": {
                            "name": "print-hello"
                        }
                    }
                }
            },
            "inputDefinitions": {
                "parameters": {
                    "message": {
                        "parameterType": "STRING"
                    }
                }
            }
        }
    }
    
    pipeline1 = create_pipeline("simple-pipeline", "A simple test pipeline", simple_pipeline_spec)
    if pipeline1:
        test_data["pipelines"].append(pipeline1)
        print(f"Created pipeline: {pipeline1['name']} (ID: {pipeline1['id']})")
        
        # Create pipeline version
        version1 = create_pipeline_version(pipeline1["id"], "v1", simple_pipeline_spec)
        if version1:
            test_data["pipelines"].append(version1)
            print(f"Created pipeline version: {version1['name']} (ID: {version1['id']})")
    
    # Create pipeline with multiple versions and different specs
    complex_pipeline_spec_v1 = {
        "schemaVersion": "2.1.0",
        "sdkVersion": "kfp-2.0.0",
        "pipelineInfo": {
            "name": "complex-pipeline"
        },
        "components": {
            "comp-data-preprocessing": {
                "executorLabel": "exec-data-preprocessing",
                "inputDefinitions": {
                    "parameters": {
                        "input_data": {
                            "parameterType": "STRING"
                        }
                    }
                }
            },
            "comp-model-training": {
                "executorLabel": "exec-model-training",
                "inputDefinitions": {
                    "parameters": {
                        "input_data": {
                            "parameterType": "STRING"
                        }
                    }
                }
            }
        },
        "deploymentSpec": {
            "executors": {
                "exec-data-preprocessing": {
                    "container": {
                        "image": "python:3.9",
                        "command": ["echo"],
                        "args": ["Processing data: {{$.inputs.parameters['input_data']}}"]
                    }
                },
                "exec-model-training": {
                    "container": {
                        "image": "python:3.9",
                        "command": ["echo"],
                        "args": ["Training model with input: {{$.inputs.parameters['input_data']}}"]
                    }
                }
            }
        },
        "root": {
            "dag": {
                "tasks": {
                    "data-preprocessing": {
                        "componentRef": {
                            "name": "comp-data-preprocessing"
                        },
                        "inputs": {
                            "parameters": {
                                "input_data": {
                                    "componentInputParameter": "input_data"
                                }
                            }
                        },
                        "taskInfo": {
                            "name": "data-preprocessing"
                        }
                    },
                    "model-training": {
                        "componentRef": {
                            "name": "comp-model-training"
                        },
                        "inputs": {
                            "parameters": {
                                "input_data": {
                                    "componentInputParameter": "input_data"
                                }
                            }
                        },
                        "taskInfo": {
                            "name": "model-training"
                        }
                    }
                }
            },
            "inputDefinitions": {
                "parameters": {
                    "input_data": {
                        "parameterType": "STRING"
                    }
                }
            }
        }
    }
    
    complex_pipeline_spec_v2 = {
        "schemaVersion": "2.1.0",
        "sdkVersion": "kfp-2.0.0",
        "pipelineInfo": {
            "name": "complex-pipeline"
        },
        "components": {
            "comp-data-preprocessing": {
                "executorLabel": "exec-data-preprocessing",
                "inputDefinitions": {
                    "parameters": {
                        "input_data": {
                            "parameterType": "STRING"
                        }
                    }
                }
            },
            "comp-model-training": {
                "executorLabel": "exec-model-training",
                "inputDefinitions": {
                    "parameters": {
                        "input_data": {
                            "parameterType": "STRING"
                        }
                    }
                }
            },
            "comp-model-evaluation": {
                "executorLabel": "exec-model-evaluation",
                "inputDefinitions": {
                    "parameters": {
                        "input_data": {
                            "parameterType": "STRING"
                        }
                    }
                }
            }
        },
        "deploymentSpec": {
            "executors": {
                "exec-data-preprocessing": {
                    "container": {
                        "image": "python:3.9",
                        "command": ["echo"],
                        "args": ["Processing data: {{$.inputs.parameters['input_data']}}"]
                    }
                },
                "exec-model-training": {
                    "container": {
                        "image": "python:3.9",
                        "command": ["echo"],
                        "args": ["Training model with input: {{$.inputs.parameters['input_data']}}"]
                    }
                },
                "exec-model-evaluation": {
                    "container": {
                        "image": "python:3.9",
                        "command": ["echo"],
                        "args": ["Evaluating model with input: {{$.inputs.parameters['input_data']}}"]
                    }
                }
            }
        },
        "root": {
            "dag": {
                "tasks": {
                    "data-preprocessing": {
                        "componentRef": {
                            "name": "comp-data-preprocessing"
                        },
                        "inputs": {
                            "parameters": {
                                "input_data": {
                                    "componentInputParameter": "input_data"
                                }
                            }
                        },
                        "taskInfo": {
                            "name": "data-preprocessing"
                        }
                    },
                    "model-training": {
                        "componentRef": {
                            "name": "comp-model-training"
                        },
                        "inputs": {
                            "parameters": {
                                "input_data": {
                                    "componentInputParameter": "input_data"
                                }
                            }
                        },
                        "taskInfo": {
                            "name": "model-training"
                        }
                    },
                    "model-evaluation": {
                        "componentRef": {
                            "name": "comp-model-evaluation"
                        },
                        "inputs": {
                            "parameters": {
                                "input_data": {
                                    "componentInputParameter": "input_data"
                                }
                            }
                        },
                        "taskInfo": {
                            "name": "model-evaluation"
                        }
                    }
                }
            },
            "inputDefinitions": {
                "parameters": {
                    "input_data": {
                        "parameterType": "STRING"
                    }
                }
            }
        }
    }
    
    pipeline2 = create_pipeline("complex-pipeline", "A complex test pipeline", complex_pipeline_spec_v1)
    if pipeline2:
        test_data["pipelines"].append(pipeline2)
        print(f"Created pipeline: {pipeline2['name']} (ID: {pipeline2['id']})")
        
        # Create two versions with different specs
        version2_1 = create_pipeline_version(pipeline2["id"], "v1", complex_pipeline_spec_v1)
        if version2_1:
            test_data["pipelines"].append(version2_1)
            print(f"Created pipeline version: {version2_1['name']} (ID: {version2_1['id']})")
        
        version2_2 = create_pipeline_version(pipeline2["id"], "v2", complex_pipeline_spec_v2)
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

