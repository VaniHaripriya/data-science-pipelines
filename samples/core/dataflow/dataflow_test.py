# Copyright 2021 The Kubeflow Authors
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

import kfp.deprecated as kfp
from kfp.samples.test.utils import TestCase, relative_path, run_pipeline_func

run_pipeline_func([
    TestCase(
        pipeline_file=relative_path(__file__, 'dataflow.ipynb'),
        arguments={
            'project_id': 'kfp-ci',
            'staging_dir': 'gs://kfp-ci/samples/dataflow',
            'region': 'us-central1',
        },
        mode=kfp.dsl.PipelineExecutionMode.V1_LEGACY,
        timeout_mins=40,
    ),
])
