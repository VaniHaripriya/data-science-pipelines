// Copyright 2021-2023 The Kubeflow Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package argocompiler

import (
	"fmt"
	"os"
	"strings"

	wfapi "github.com/argoproj/argo-workflows/v3/pkg/apis/workflow/v1alpha1"
	"github.com/kubeflow/pipelines/api/v2alpha1/go/pipelinespec"
	"github.com/kubeflow/pipelines/backend/src/v2/component"
	"github.com/kubeflow/pipelines/kubernetes_platform/go/kubernetesplatform"
	k8score "k8s.io/api/core/v1"
)

const (
	volumeNameKFPLauncher   = "kfp-launcher"
	volumeNameCABUndle      = "ca-bundle"
	DefaultLauncherImage    = "gcr.io/ml-pipeline/kfp-launcher@sha256:80cf120abd125db84fa547640fd6386c4b2a26936e0c2b04a7d3634991a850a4"
	LauncherImageEnvVar     = "V2_LAUNCHER_IMAGE"
	DefaultDriverImage      = "gcr.io/ml-pipeline/kfp-driver@sha256:8e60086b04d92b657898a310ca9757631d58547e76bbbb8bfc376d654bef1707"
	DriverImageEnvVar       = "V2_DRIVER_IMAGE"
	gcsScratchLocation      = "/gcs"
	gcsScratchName          = "gcs-scratch"
	s3ScratchLocation       = "/s3"
	s3ScratchName           = "s3-scratch"
	minioScratchLocation    = "/minio"
	minioScratchName        = "minio-scratch"
	dotLocalScratchLocation = "/.local"
	dotLocalScratchName     = "dot-local-scratch"
	dotCacheScratchLocation = "/.cache"
	dotCacheScratchName     = "dot-cache-scratch"
	dotConfigScratchLocation = "/.config"
	dotConfigScratchName     = "dot-config-scratch"
)

func (c *workflowCompiler) Container(name string, component *pipelinespec.ComponentSpec, container *pipelinespec.PipelineDeploymentConfig_PipelineContainerSpec) error {
	err := c.saveComponentSpec(name, component)
	if err != nil {
		return err
	}
	err = c.saveComponentImpl(name, container)
	if err != nil {
		return err
	}
	return nil
}

type containerDriverOutputs struct {
	podSpecPatch string
	cached       string
	condition    string
}

type containerDriverInputs struct {
	component        string
	task             string
	container        string
	parentDagID      string
	iterationIndex   string // optional, when this is an iteration task
	kubernetesConfig string // optional, used when Kubernetes config is not empty
}

func GetLauncherImage() string {
	launcherImage := os.Getenv(LauncherImageEnvVar)
	if launcherImage == "" {
		launcherImage = DefaultLauncherImage
	}
	return launcherImage
}

func GetDriverImage() string {
	driverImage := os.Getenv(DriverImageEnvVar)
	if driverImage == "" {
		driverImage = DefaultDriverImage
	}
	return driverImage
}

func (c *workflowCompiler) containerDriverTask(name string, inputs containerDriverInputs) (*wfapi.DAGTask, *containerDriverOutputs) {
	dagTask := &wfapi.DAGTask{
		Name:     name,
		Template: c.addContainerDriverTemplate(),
		Arguments: wfapi.Arguments{
			Parameters: []wfapi.Parameter{
				{Name: paramComponent, Value: wfapi.AnyStringPtr(inputs.component)},
				{Name: paramTask, Value: wfapi.AnyStringPtr(inputs.task)},
				{Name: paramContainer, Value: wfapi.AnyStringPtr(inputs.container)},
				{Name: paramParentDagID, Value: wfapi.AnyStringPtr(inputs.parentDagID)},
			},
		},
	}
	if inputs.iterationIndex != "" {
		dagTask.Arguments.Parameters = append(
			dagTask.Arguments.Parameters,
			wfapi.Parameter{Name: paramIterationIndex, Value: wfapi.AnyStringPtr(inputs.iterationIndex)},
		)
	}
	if inputs.kubernetesConfig != "" {
		dagTask.Arguments.Parameters = append(
			dagTask.Arguments.Parameters,
			wfapi.Parameter{Name: paramKubernetesConfig, Value: wfapi.AnyStringPtr(inputs.kubernetesConfig)},
		)
	}
	outputs := &containerDriverOutputs{
		podSpecPatch: taskOutputParameter(name, paramPodSpecPatch),
		cached:       taskOutputParameter(name, paramCachedDecision),
		condition:    taskOutputParameter(name, paramCondition),
	}
	return dagTask, outputs
}

func (c *workflowCompiler) addContainerDriverTemplate() string {
	name := "system-container-driver"
	_, ok := c.templates[name]
	if ok {
		return name
	}
	t := &wfapi.Template{
		Name: name,
		Inputs: wfapi.Inputs{
			Parameters: []wfapi.Parameter{
				{Name: paramComponent},
				{Name: paramTask},
				{Name: paramContainer},
				{Name: paramParentDagID},
				{Name: paramIterationIndex, Default: wfapi.AnyStringPtr("-1")},
				{Name: paramKubernetesConfig, Default: wfapi.AnyStringPtr("")},
			},
		},
		Outputs: wfapi.Outputs{
			Parameters: []wfapi.Parameter{
				{Name: paramPodSpecPatch, ValueFrom: &wfapi.ValueFrom{Path: "/tmp/outputs/pod-spec-patch", Default: wfapi.AnyStringPtr("")}},
				{Name: paramCachedDecision, Default: wfapi.AnyStringPtr("false"), ValueFrom: &wfapi.ValueFrom{Path: "/tmp/outputs/cached-decision", Default: wfapi.AnyStringPtr("false")}},
				{Name: paramCondition, ValueFrom: &wfapi.ValueFrom{Path: "/tmp/outputs/condition", Default: wfapi.AnyStringPtr("true")}},
			},
		},
		Container: &k8score.Container{
			Image:   GetDriverImage(),
			Command: []string{"driver"},
			Args: []string{
				"--type", "CONTAINER",
				"--pipeline_name", c.spec.GetPipelineInfo().GetName(),
				"--run_id", runID(),
				"--dag_execution_id", inputValue(paramParentDagID),
				"--component", inputValue(paramComponent),
				"--task", inputValue(paramTask),
				"--container", inputValue(paramContainer),
				"--iteration_index", inputValue(paramIterationIndex),
				"--cached_decision_path", outputPath(paramCachedDecision),
				"--pod_spec_patch_path", outputPath(paramPodSpecPatch),
				"--condition_path", outputPath(paramCondition),
				"--kubernetes_config", inputValue(paramKubernetesConfig),
			},
			Resources: driverResources,
		},
	}
	c.templates[name] = t
	c.wf.Spec.Templates = append(c.wf.Spec.Templates, *t)
	return name
}

type containerExecutorInputs struct {
	// a strategic patch of pod spec merged with runtime Pod spec.
	podSpecPatch string
	// if true, the container will be cached.
	cachedDecision string
	// if false, the container will be skipped.
	condition string
}

// containerExecutorTask returns an argo workflows DAGTask.
// name: argo workflows DAG task name
// The other arguments are argo workflows task parameters, they can be either a
// string or a placeholder.
func (c *workflowCompiler) containerExecutorTask(name string, inputs containerExecutorInputs, refName string) *wfapi.DAGTask {
	when := ""
	if inputs.condition != "" {
		when = inputs.condition + " != false"
	}
	return &wfapi.DAGTask{
		Name:     name,
		Template: c.addContainerExecutorTemplate(refName),
		When:     when,
		Arguments: wfapi.Arguments{
			Parameters: []wfapi.Parameter{
				{Name: paramPodSpecPatch, Value: wfapi.AnyStringPtr(inputs.podSpecPatch)},
				{Name: paramCachedDecision, Value: wfapi.AnyStringPtr(inputs.cachedDecision), Default: wfapi.AnyStringPtr("false")},
			},
		},
	}
}

// addContainerExecutorTemplate adds a generic container executor template for
// any container component task.
// During runtime, it's expected that pod-spec-patch will specify command, args
// and resources etc, that are different for different tasks.
func (c *workflowCompiler) addContainerExecutorTemplate(refName string) string {
	// container template is parent of container implementation template
	nameContainerExecutor := "system-container-executor"
	nameContainerImpl := "system-container-impl"
	_, ok := c.templates[nameContainerExecutor]
	if ok {
		return nameContainerExecutor
	}
	container := &wfapi.Template{
		Name: nameContainerExecutor,
		Inputs: wfapi.Inputs{
			Parameters: []wfapi.Parameter{
				{Name: paramPodSpecPatch},
				{Name: paramCachedDecision, Default: wfapi.AnyStringPtr("false")},
			},
		},
		DAG: &wfapi.DAGTemplate{
			Tasks: []wfapi.DAGTask{{
				Name:     "executor",
				Template: nameContainerImpl,
				Arguments: wfapi.Arguments{
					Parameters: []wfapi.Parameter{{
						Name:  paramPodSpecPatch,
						Value: wfapi.AnyStringPtr(inputParameter(paramPodSpecPatch)),
					}},
				},
				// When cached decision is true, the container
				// implementation template will be skipped, but
				// container executor template is still considered
				// to have succeeded.
				// This makes sure downstream tasks are not skipped.
				When: inputParameter(paramCachedDecision) + " != true",
			}},
		},
	}
	c.templates[nameContainerExecutor] = container
	executor := &wfapi.Template{
		Name: nameContainerImpl,
		Inputs: wfapi.Inputs{
			Parameters: []wfapi.Parameter{
				{Name: paramPodSpecPatch},
			},
		},
		// PodSpecPatch input param is where actual image, command and
		// args come from. It is treated as a strategic merge patch on
		// top of the Pod spec.
		PodSpecPatch: inputValue(paramPodSpecPatch),
		Volumes: []k8score.Volume{
			{
				Name: volumeNameKFPLauncher,
				VolumeSource: k8score.VolumeSource{
					EmptyDir: &k8score.EmptyDirVolumeSource{},
				},
			},
			{
				Name: gcsScratchName,
				VolumeSource: k8score.VolumeSource{
					EmptyDir: &k8score.EmptyDirVolumeSource{},
				},
			},
			{
				Name: s3ScratchName,
				VolumeSource: k8score.VolumeSource{
					EmptyDir: &k8score.EmptyDirVolumeSource{},
				},
			},
			{
				Name: minioScratchName,
				VolumeSource: k8score.VolumeSource{
					EmptyDir: &k8score.EmptyDirVolumeSource{},
				},
			},
			{
				Name: dotLocalScratchName,
				VolumeSource: k8score.VolumeSource{
					EmptyDir: &k8score.EmptyDirVolumeSource{},
				},
			},
			{
				Name: dotCacheScratchName,
				VolumeSource: k8score.VolumeSource{
					EmptyDir: &k8score.EmptyDirVolumeSource{},
				},
			},
			{
				Name: dotConfigScratchName,
				VolumeSource: k8score.VolumeSource{
					EmptyDir: &k8score.EmptyDirVolumeSource{},
				},
			},
		},
		InitContainers: []wfapi.UserContainer{{
			Container: k8score.Container{
				Name:    "kfp-launcher",
				Image:   GetLauncherImage(),
				Command: []string{"launcher-v2", "--copy", component.KFPLauncherPath},
				VolumeMounts: []k8score.VolumeMount{
					{
						Name:      volumeNameKFPLauncher,
						MountPath: component.VolumePathKFPLauncher,
					},
				},
				Resources: launcherResources,
			},
		}},
		Container: &k8score.Container{
			// The placeholder image and command should always be
			// overridden in podSpecPatch.
			// In case we have a bug, the placeholder image is kept
			// in gcr.io/ml-pipeline, so that we are sure the image
			// never exists.
			// These are added to pass argo workflows linting.
			Image:   "gcr.io/ml-pipeline/should-be-overridden-during-runtime",
			Command: []string{"should-be-overridden-during-runtime"},
			VolumeMounts: []k8score.VolumeMount{
				{
					Name:      volumeNameKFPLauncher,
					MountPath: component.VolumePathKFPLauncher,
				},
				{
					Name:      gcsScratchName,
					MountPath: gcsScratchLocation,
				},
				{
					Name:      s3ScratchName,
					MountPath: s3ScratchLocation,
				},
				{
					Name:      minioScratchName,
					MountPath: minioScratchLocation,
				},
				{
					Name:      dotLocalScratchName,
					MountPath: dotLocalScratchLocation,
				},
				{
					Name:      dotCacheScratchName,
					MountPath: dotCacheScratchLocation,
				},
				{
					Name:      dotConfigScratchName,
					MountPath: dotConfigScratchLocation,
				},
			},
			EnvFrom: []k8score.EnvFromSource{metadataEnvFrom},
			Env:     commonEnvs,
		},
	}
	caBundleCfgMapName := os.Getenv("ARTIFACT_COPY_STEP_CABUNDLE_CONFIGMAP_NAME")
	caBundleCfgMapKey := os.Getenv("ARTIFACT_COPY_STEP_CABUNDLE_CONFIGMAP_KEY")
	caBundleMountPath := os.Getenv("ARTIFACT_COPY_STEP_CABUNDLE_MOUNTPATH")
	if caBundleCfgMapName != "" && caBundleCfgMapKey != "" {
		caFile := fmt.Sprintf("%s/%s", caBundleMountPath, caBundleCfgMapKey)
		var certDirectories = []string{
			caBundleMountPath,
			"/etc/ssl/certs",
			"/etc/pki/tls/certs",
		}
		// Add to REQUESTS_CA_BUNDLE for python request library.
		// As many python web based libraries utilize this, we add it here so the user
		// does not have to manually include this in the user pipeline.
		// Note: for packages like Boto3, even though it is documented to use AWS_CA_BUNDLE,
		// we found the python boto3 client only works if we include REQUESTS_CA_BUNDLE.
		// https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification
		// https://github.com/aws/aws-cli/issues/3425
		executor.Container.Env = append(executor.Container.Env, k8score.EnvVar{
			Name:  "REQUESTS_CA_BUNDLE",
			Value: caFile,
		})
		// For AWS utilities like cli, and packages.
		executor.Container.Env = append(executor.Container.Env, k8score.EnvVar{
			Name:  "AWS_CA_BUNDLE",
			Value: caFile,
		})
		// OpenSSL default cert file env variable.
		// Similar to AWS_CA_BUNDLE, the SSL_CERT_DIR equivalent for paths had unyielding
		// results, even after rehashing.
		// https://www.openssl.org/docs/man1.1.1/man3/SSL_CTX_set_default_verify_paths.html
		executor.Container.Env = append(executor.Container.Env, k8score.EnvVar{
			Name:  "SSL_CERT_FILE",
			Value: caFile,
		})
		sslCertDir := strings.Join(certDirectories, ":")
		executor.Container.Env = append(executor.Container.Env, k8score.EnvVar{
			Name:  "SSL_CERT_DIR",
			Value: sslCertDir,
		})
		volume := k8score.Volume{
			Name: volumeNameCABUndle,
			VolumeSource: k8score.VolumeSource{
				ConfigMap: &k8score.ConfigMapVolumeSource{
					LocalObjectReference: k8score.LocalObjectReference{
						Name: caBundleCfgMapName,
					},
				},
			},
		}

		executor.Volumes = append(executor.Volumes, volume)

		volumeMount := k8score.VolumeMount{
			Name:      volumeNameCABUndle,
			MountPath: caFile,
			SubPath:   caBundleCfgMapKey,
		}

		executor.Container.VolumeMounts = append(executor.Container.VolumeMounts, volumeMount)

	}
	c.templates[nameContainerImpl] = executor
	c.wf.Spec.Templates = append(c.wf.Spec.Templates, *container, *executor)
	return nameContainerExecutor
}

// Extends the PodMetadata to include Kubernetes-specific executor config.
// Although the current podMetadata object is always empty, this function
// doesn't overwrite the existing podMetadata because for security reasons
// the existing podMetadata should have higher privilege than the user definition.
func extendPodMetadata(
	podMetadata *wfapi.Metadata,
	kubernetesExecutorConfig *kubernetesplatform.KubernetesExecutorConfig,
) {
	// Get pod metadata information
	if kubernetesExecutorConfig.GetPodMetadata() != nil {
		labels := kubernetesExecutorConfig.GetPodMetadata().GetLabels()
		if labels != nil {
			if podMetadata.Labels == nil {
				podMetadata.Labels = labels
			} else {
				podMetadata.Labels = extendMetadataMap(podMetadata.Labels, labels)
			}
		}
		annotations := kubernetesExecutorConfig.GetPodMetadata().GetAnnotations()
		if annotations != nil {
			if podMetadata.Annotations == nil {
				podMetadata.Annotations = annotations
			} else {
				podMetadata.Annotations = extendMetadataMap(podMetadata.Annotations, annotations)
			}
		}
	}
}

// Extends metadata map values, highPriorityMap should overwrites lowPriorityMap values
// The original Map inputs should have higher priority since its defined by admin
// TODO: Use maps.Copy after moving to go 1.21+
func extendMetadataMap(
	highPriorityMap map[string]string,
	lowPriorityMap map[string]string,
) map[string]string {
	for k, v := range highPriorityMap {
		lowPriorityMap[k] = v
	}
	return lowPriorityMap
}
