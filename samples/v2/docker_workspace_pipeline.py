# Copyright 2023 The Kubeflow Authors
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

"""A sample pipeline demonstrating DockerRunner workspace functionality.

This pipeline shows how to use the DockerRunner with workspace support,
allowing components to share persistent storage across tasks when running
locally with Docker containers.
"""

from kfp import dsl
from kfp import local


@dsl.component
def write_to_workspace(text: str, workspace_path: str) -> str:
    """Write text to a file in the workspace and return the file path."""
    import os
    
    # Create a subdirectory in the workspace
    output_dir = os.path.join(workspace_path, 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    # Write the text to a file
    output_file = os.path.join(output_dir, 'output.txt')
    with open(output_file, 'w') as f:
        f.write(text)
    
    print(f"Wrote text to workspace file: {output_file}")
    return output_file


@dsl.component
def read_from_workspace(file_path: str) -> str:
    """Read and return the content of a file from the workspace."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    print(f"Read content from workspace file: {file_path}")
    print(f"Content: {content}")
    return content


@dsl.component
def process_data_in_workspace(input_file: str, workspace_path: str) -> str:
    """Process data from a file and write results back to the workspace."""
    import os
    import json
    
    # Read the input file
    with open(input_file, 'r') as f:
        input_text = f.read()
    
    # Process the data (simple example: count characters and create summary)
    char_count = len(input_text)
    word_count = len(input_text.split())
    summary = {
        'input_text': input_text,
        'character_count': char_count,
        'word_count': word_count,
        'processed_at': '2024-01-01T00:00:00Z'
    }
    
    # Write results to workspace
    output_dir = os.path.join(workspace_path, 'results')
    os.makedirs(output_dir, exist_ok=True)
    
    summary_file = os.path.join(output_dir, 'summary.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Processed data and wrote summary to: {summary_file}")
    return summary_file


@dsl.pipeline(
    name="docker-workspace-pipeline",
    description="A pipeline demonstrating DockerRunner workspace functionality",
    pipeline_config=dsl.PipelineConfig(
        workspace=dsl.WorkspaceConfig(
            size='1Gi',
            kubernetes=dsl.KubernetesWorkspaceConfig(
                pvcSpecPatch={'storageClassName': 'standard'}
            )
        ),
    ),
)
def docker_workspace_pipeline(text: str = "Hello from Docker workspace!") -> str:
    """A pipeline using DockerRunner with workspace functionality.
    
    This pipeline demonstrates:
    1. Writing data to the shared workspace
    2. Reading data from the workspace
    3. Processing data and storing results in the workspace
    4. Sharing data between tasks through the workspace
    
    Args:
        text: The text to write to the workspace
        
    Returns:
        The path to the final summary file
    """
    
    # Write initial data to workspace
    write_task = write_to_workspace(
        text=text,
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER
    )
    
    # Read the data back from workspace
    read_task = read_from_workspace(
        file_path=write_task.output
    )
    
    # Process the data and store results in workspace
    process_task = process_data_in_workspace(
        input_file=write_task.output,
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER
    )
    
    return process_task.output


if __name__ == "__main__":
    # Example of running the pipeline locally with DockerRunner
    print("To run this pipeline locally with DockerRunner:")
    print("1. Make sure Docker is running")
    print("2. Install the docker Python package: pip install docker")
    print("3. Run the following code:")
    print()
    print("from kfp import local")
    print("local.init(")
    print("    runner=local.DockerRunner(),")
    print("    pipeline_root='./local_outputs',")
    print("    workspace_root='./workspace'")
    print(")")
    print()
    print("result = docker_workspace_pipeline(text='Custom text for Docker workspace!')")
    print("print(f'Pipeline result: {result}')")
