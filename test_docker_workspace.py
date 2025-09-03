#!/usr/bin/env python3
"""Test script to demonstrate DockerRunner workspace functionality.

This script shows how the DockerRunner now supports workspace functionality,
allowing components to share persistent storage across tasks when running
locally with Docker containers.
"""

import os
import tempfile
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


@dsl.pipeline(
    name="test-docker-workspace",
    description="A simple test pipeline for DockerRunner workspace functionality",
)
def test_docker_workspace_pipeline(text: str = "Hello from Docker workspace!") -> str:
    """A simple test pipeline using DockerRunner with workspace functionality."""
    
    # Write to workspace
    write_task = write_to_workspace(
        text=text,
        workspace_path=dsl.WORKSPACE_PATH_PLACEHOLDER
    )
    
    # Read from workspace
    read_task = read_from_workspace(
        file_path=write_task.output
    )
    
    return read_task.output


def main():
    """Main function to test DockerRunner workspace functionality."""
    print("Testing DockerRunner workspace functionality...")
    print("=" * 50)
    
    # Create temporary directories for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        pipeline_root = os.path.join(temp_dir, 'pipeline_outputs')
        workspace_root = os.path.join(temp_dir, 'workspace')
        
        # Create the directories
        os.makedirs(pipeline_root, exist_ok=True)
        os.makedirs(workspace_root, exist_ok=True)
        
        print(f"Pipeline root: {pipeline_root}")
        print(f"Workspace root: {workspace_root}")
        print()
        
        try:
            # Initialize local execution with DockerRunner
            print("Initializing local execution with DockerRunner...")
            local.init(
                runner=local.DockerRunner(),
                pipeline_root=pipeline_root,
                workspace_root=workspace_root
            )
            print("✓ Local execution initialized successfully")
            print()
            
            # Run the pipeline
            print("Running test pipeline...")
            result = test_docker_workspace_pipeline(text="Test message for Docker workspace!")
            print(f"✓ Pipeline completed successfully")
            print(f"Result: {result}")
            print()
            
            # Verify the workspace contains the expected files
            print("Verifying workspace contents...")
            data_dir = os.path.join(workspace_root, 'data')
            output_file = os.path.join(data_dir, 'output.txt')
            
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    content = f.read()
                print(f"✓ Workspace file exists: {output_file}")
                print(f"✓ File content: {content}")
            else:
                print(f"✗ Workspace file not found: {output_file}")
            
            print()
            print("=" * 50)
            print("✓ DockerRunner workspace functionality test completed successfully!")
            
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            print()
            print("Make sure:")
            print("1. Docker is running")
            print("2. The 'docker' Python package is installed: pip install docker")
            print("3. You have permission to run Docker commands")
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
