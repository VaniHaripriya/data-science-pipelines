#!/bin/bash
#
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

# This is a wrapper script on top of test.sh, it installs required dependencies.

set -ex

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null && pwd)"
TMP="$(mktemp -d)"

pushd "${TMP}"


# Reference: https://github.com/mikefarah/yq/releases/tag/3.4.1
curl -s -LO "https://github.com/mikefarah/yq/releases/download/3.4.1/yq_linux_amd64"
chmod +x yq_linux_amd64
mv yq_linux_amd64 /usr/local/bin/yq

# Install kpt
KPT_VERSION=1.0.0-beta.54
curl -s -LO "https://github.com/GoogleContainerTools/kpt/releases/download/v${KPT_VERSION}/kpt_linux_amd64"
tar -xzf kpt_linux_amd64-${KPT_VERSION}.tar.gz
mv kpt /usr/local/bin/kpt

popd

# kubectl should already be installed in google-github-actions/setup-gcloud@v2:latest
# so we do not need to install them here

# trigger real unit tests
${DIR}/test.sh
# verify release script runs properly

${DIR}/release.sh v1.2.3-dummy
# --no-pager sends output to stdout
# Show git diff, so people can manually verify results of the release script
git --no-pager diff
