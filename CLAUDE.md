# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Kubeflow Pipelines (KFP) is a platform for building and deploying portable, scalable machine learning (ML) workflows on Kubernetes. The system orchestrates containerized ML workloads using Argo Workflows as the execution engine, with MySQL for persistence and a React-based web UI for visualization.

## Architecture

KFP consists of several key components:

**Backend Services (Go)**:
- `api-server` (`backend/src/apiserver/`) - Main REST API server handling pipeline/run/experiment management
- `persistence-agent` - Syncs workflow state from Argo to MySQL
- `scheduled-workflow` (`backend/src/crd/controller/scheduledworkflow/`) - Manages recurring pipeline runs
- `viewer-controller` - Manages Tensorboard viewer instances
- `cache-server` - Handles execution caching
- `driver` & `launcher` (`backend/src/v2/`) - V2 runtime components that execute in pods

**Frontend (TypeScript/React)**:
- Client UI (`frontend/src/`) + Node.js server (`frontend/server/`)

**SDK (Python)**:
- `kfp` package (`sdk/python/`) - Python SDK for authoring pipelines
- Compiler translates Python DSL to Argo YAML or IR YAML (v2)

**Dependencies**:
- Argo Workflows v3.5-v3.7 - Workflow execution engine
- MySQL v8 - Metadata storage
- MinIO - Object storage for artifacts

The system uses a layered architecture where users author pipelines with the Python SDK, the compiler translates them to Kubernetes CRDs, Argo executes the workflows, and backend services persist state and expose APIs for the frontend.

## Key Architectural Patterns

### API Server Resource Manager

The `ResourceManager` (`backend/src/apiserver/resource/resource_manager.go`) is the central orchestrator for run lifecycle:

**Run Lifecycle Hooks**:
- `CreateRun`: Validates pipeline spec, creates workflow CR, applies plugin hooks (e.g., MLflow)
- `ReportWorkflowResource`: Called by persistence-agent when workflow state changes; handles terminal state logic
- `RetryRun`: Generates new workflow from failed run, reopens plugin resources

**Plugin Integration Pattern**:
Plugins integrate via lifecycle hooks without modifying core run logic:
```go
// Example pattern from MLflow integration
func (r *ResourceManager) CreateRun(ctx context.Context, run *model.Run) (*model.Run, error) {
    // 1. Parse plugin input from run.PluginsInputString
    pluginInput := resolvePluginInput(run)

    // 2. Generate workflow spec
    executionSpec := tmpl.RunWorkflow(run, runWorkflowOptions)

    // 3. Apply plugin hooks (e.g., create MLflow parent run, inject env vars)
    r.applyPluginOnRunStart(ctx, run, namespace, pluginInput, executionSpec)

    // 4. Create workflow CR
    newExecSpec := r.getWorkflowClient(namespace).Create(ctx, executionSpec, ...)

    // 5. Persist run with plugins_output
    r.runStore.CreateRun(run)
}
```

### Configuration Management

**Two-Level Configuration Pattern** (used by plugins like MLflow):

1. **Global Config** (API server YAML): Base configuration for all namespaces
   ```yaml
   plugins:
     mlflow:
       endpoint: "https://mlflow.example.com"
       timeout: "30s"
       settings:
         authType: "kubernetes"
         workspacesEnabled: true
   ```

2. **Namespace Config** (ConfigMap `kfp-launcher` in each namespace): Overrides global config
   ```json
   {
     "endpoint": "https://mlflow-ns.example.com",
     "settings": {
       "authType": "bearer",
       "credentialSecretRef": {"name": "mlflow-token"}
     }
   }
   ```

**Resolution Logic**:
- Namespace config overrides global config (endpoint, timeout, TLS, settings)
- If namespace overrides endpoint, it MUST provide its own credentials
- See `resource_manager.go:resolveMLflowRequestConfig` for merge logic

### Database Schema Management

The backend uses **GORM** with auto-migration:
- Schema changes happen automatically on first deployment with new model fields
- Add fields to model structs in `backend/src/apiserver/model/`
- Use `*LargeText` for nullable large text fields (e.g., `PluginsInputString`)
- For complex migrations, use `backend/src/apiserver/storage/db.go:initDB()`

**Important**: Fields in model structs use GORM tags:
```go
type RunDetails struct {
    PluginsInputString  *LargeText `gorm:"column:PluginsInput; default:null;"`
    PluginsOutputString *LargeText `gorm:"column:PluginsOutput; default:null;"`
}
```

### Workflow Environment Variable Injection

Driver and launcher need access to plugin runtime context (e.g., MLflow tracking URI). Use `SetEnvVarsToDriverAndLauncherTemplates`:

```go
// In CreateRun after executionSpec is generated
envVars := map[string]string{
    "KFP_MLFLOW_TRACKING_URI":  "https://mlflow.example.com",
    "KFP_MLFLOW_PARENT_RUN_ID": "abc123",
}
executionSpec.SetEnvVarsToDriverAndLauncherTemplates(envVars)
```

**Template Identification**:
- Driver templates: name contains "driver" (case-insensitive)
- Launcher templates: name is "system-container-impl" OR has "kfp-launcher" init container

### Plugin Output State Management

Plugins track their own state separately from pipeline run state:

```go
// plugins_output.mlflow structure
{
  "entries": {
    "experiment_id": {"value": "42"},
    "run_url": {"value": "https://...", "content_type": "URL"}
  },
  "state": "SUCCEEDED",  // or "FAILED"
  "state_message": ""    // Error details if state is FAILED
}
```

**Key Pattern**: Plugin failures (e.g., MLflow server unreachable) don't fail the pipeline run. The run continues with `plugins_output.<plugin>.state = FAILED` and descriptive `state_message`.

### Workflow Metrics Collection

The persistence agent collects metrics from completed workflow nodes:

**How it works**:
1. Components output metrics to `mlpipeline-metrics` artifact (JSON file in tar.gz)
2. Persistence agent reads artifact via `ReadArtifactRequest`
3. Metrics are stored in `run_metrics` table with `RunUUID` and `NodeID`

**Artifact reading pattern** (`workflow.go:CollectionMetrics`):
```go
// Used by persistence agent
func (w *Workflow) CollectionMetrics(
    readArtifact func(*artifactclient.ReadArtifactRequest) (*artifactclient.ReadArtifactResponse, error),
) ([]*api.RunMetric, []error) {
    for _, nodeStatus := range w.Status.Nodes {
        artifactRequest := &artifactclient.ReadArtifactRequest{
            RunID:        runID,
            NodeID:       nodeStatus.ID,
            ArtifactName: "mlpipeline-metrics",
        }
        artifactResponse, err := readArtifact(artifactRequest)
        // Extract metrics from tar.gz, parse JSON, store in DB
    }
}
```

**Important**: `ReadArtifact` function signature changed from `api.ReadArtifactRequest` to `artifactclient.ReadArtifactRequest` (field names changed from `RunId/NodeId` to `RunID/NodeID`).

## Common Commands

### Quick Commands (using `just`)

The repository includes an optional `just` command runner for convenience. All recipes wrap existing `make` targets:

```bash
just                          # List available recipes
just backend-test             # Run backend v2 Go unit tests
just backend-images           # Build all backend Docker images
just backend-lint-format      # Lint and format Go code
just kind-standalone          # Create Kind cluster with KFP
just kind-dev                 # Create Kind cluster for API server development
just api-protos               # Build API v2alpha1 Go and Python artifacts
just sdk-build                # Build SDK Python distribution
```

### Backend Development

**Building**:
```bash
# Build API server binary
go build -o /tmp/apiserver backend/src/apiserver/*.go

# Build all backend images (from repo root)
make -C backend image_all

# Build specific component
make -C backend image_apiserver
make -C backend image_driver
```

**Testing**:
```bash
# Run all backend unit tests
go test -v -cover ./backend/...

# Run v2 engine tests
make -C backend/src/v2 test

# Run integration tests (requires local API server running)
LOCAL_API_SERVER=true go test -v ./backend/test/v2/integration/... -namespace kubeflow -args -runIntegrationTests=true

# Run specific test
go test -v ./backend/test/v2/integration/... -run 'TestCache/TestCacheSingleRun'
```

**Linting/Formatting**:
```bash
make -C backend lint          # Lint Go code
make -C backend format        # Format Go code
make -C backend lint-and-format
```

**Local Development**:
```bash
# Create Kind cluster with KFP (API server scaled to 0 for local development)
make -C backend dev-kind-cluster

# Access database directly
kubectl run -it --rm --image=docker.io/library/mysql:8.4 --restart=Never mysql-client -- mysql -h mysql
# or from localhost
mysql -h 127.0.0.1 -u root

# Check logs
kubectl logs -n kubeflow $(kubectl get pods -l app=ml-pipeline -o jsonpath='{.items[0].metadata.name}' -n kubeflow)
```

### Frontend Development

**Setup**:
```bash
cd frontend
npm ci                        # Install dependencies
npm run build                 # Build production bundle
```

**Development**:
```bash
# Deploy KFP and scale down UI
make -C backend kind-cluster-agnostic
kubectl -n kubeflow scale --replicas=0 deployment/ml-pipeline-ui

# Run frontend locally
cd frontend
npm run start:proxy-and-server  # Server at http://localhost:3001
npm run start                    # Dev server with hot reload at http://localhost:3000
```

**Testing**:
```bash
cd frontend
npm test                      # Run tests
npm run lint                  # Lint TypeScript/React
npm run format                # Format with prettier
```

### SDK Development

**Setup**:
```bash
# Create virtual environment
python -m venv env && source ./env/bin/activate
python -m pip install -U pip wheel setuptools

# Install dev dependencies
pip install -r sdk/python/requirements-dev.txt

# Install SDK in editable mode
pip install -e sdk/python

# Install dependencies (proto & kubernetes_platform)
cd api && make generate python-dev && cd ..
cd kubernetes_platform && make python-dev && cd ..
```

**Testing**:
```bash
pytest                        # Run all SDK tests from repo root
pytest -n auto                # Run tests in parallel
pytest sdk/python/kfp/compiler  # Test specific module
```

**Code Quality**:
```bash
# From repo root
yapf --in-place --recursive ./sdk/python         # Format code
docformatter --in-place --recursive ./sdk/python  # Format docstrings
isort sdk/python                                   # Sort imports
pylint ./sdk/python/kfp                           # Lint
mypy ./sdk/python/kfp/                            # Type check
```

### Regenerating Generated Files

After modifying proto files:
```bash
cd api && make all && cd ..                    # Regenerate API protos
cd kubernetes_platform && make all && cd ..    # Regenerate platform protos
make check-diff                                # Verify no uncommitted changes
```

### Pre-commit Hooks

Install pre-commit hooks to automate linting:
```bash
pip install pre-commit
pre-commit install
```

Hooks enforce:
- Python: yapf, isort, docformatter, pycln, flake8
- Go: golangci-lint (format & lint)
- General: trailing whitespace, EOF, YAML/JSON validation, no direct commits to master

## Development Workflow

### Creating a Feature or Fix

1. **Create feature branch** from master (main branch)
2. **Make changes** following code style guidelines
3. **Test locally**:
   - Backend: `go test ./backend/...`
   - Frontend: `npm test`
   - SDK: `pytest`
4. **Format code**: pre-commit hooks handle this automatically
5. **Commit with DCO**: All commits must include `Signed-off-by` line (see CONTRIBUTING.md)
6. **Create PR** following title convention

### Pull Request Title Convention

PRs must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>[ Fixes #<issue-number>]
```

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `chore` - Other changes (no user impact)
- `test` - Test-only changes
- `refactor` - Code refactoring
- `perf` - Performance improvements

**Scopes** (optional):
- `frontend` - UI/frontend server (`frontend/`)
- `backend` - Backend services (`backend/`)
- `sdk` - Python SDK (`sdk/`)
- `sdk/client` - API client (`backend/api/python_http_client`)
- `components` - Pipeline components (`components/`)
- `deployment` - Manifests (`manifests/`)
- `metadata` - MLMD related (`backend/metadata_writer`)
- `cache` - Caching (`backend/src/cache`)
- `swf` - Scheduled workflow (`backend/src/crd/controller/scheduledworkflow`)

**Examples**:
- `fix(ui): fixes empty page. Fixes #1234`
- `feat(backend): configurable service account. Fixes #1234, fixes #1235`
- `test: fix CI failure. Part of #1234`

## Testing Strategy

**Unit Tests**:
- Backend: Table-driven tests in separate `_test.go` files; use `_test` package suffix for public API tests
- SDK: pytest with fixtures
- Frontend: Jest + React Testing Library

**Backend Unit Test Pattern**:
```go
func TestWorkflow_SetEnvVarsToDriverAndLauncherTemplates(t *testing.T) {
    workflow := NewWorkflow(&workflowapi.Workflow{
        Spec: workflowapi.WorkflowSpec{
            Templates: []workflowapi.Template{
                {Name: "system-dag-driver", Container: &corev1.Container{}},
                {Name: "system-container-impl", Container: &corev1.Container{}},
                {Name: "user-template", Container: &corev1.Container{}},
            },
        },
    })

    workflow.SetEnvVarsToDriverAndLauncherTemplates(map[string]string{
        "KFP_VAR": "value",
    })

    // Assert driver and launcher have env var
    assert.Contains(t, workflow.Spec.Templates[0].Container.Env,
        corev1.EnvVar{Name: "KFP_VAR", Value: "value"})
    // Assert user template unchanged
    assert.Empty(t, workflow.Spec.Templates[2].Container.Env)
}
```

**Integration Tests**:
- Located in `backend/test/v2/integration/`
- Require running API server (local or Kind cluster)
- Run with `LOCAL_API_SERVER=true` and `-args -runIntegrationTests=true`

**E2E Tests**:
- Located in `test/`
- Deploy full KFP stack in Kind cluster
- Test complete pipeline execution workflows

**Testing ResourceManager Changes**:

When adding new ResourceManager methods or modifying run lifecycle:

1. Mock dependencies (k8s client, storage):
   ```go
   clientSet := k8sfake.NewSimpleClientset()
   fakeKubeClient := &fakeKubernetesCoreClientWithClientSet{clientSet: clientSet}
   resourceManager := NewResourceManager(
       fakeKubeClient,
       &FakePipelineStore{},
       &FakeRunStore{},
       // ... other mocks
   )
   ```

2. Test both success and failure paths
3. Verify plugin outputs are persisted correctly
4. Check that errors are gracefully handled (warnings logged, run continues)

## Code Style Guidelines

### Backend (Go)
- Follow [Google's Go Style Guide](https://google.github.io/styleguide/go/)
- Use `golangci-lint` (config: `.golangci.yaml`)
- Place tests in separate package (`package_test`) to test public API
- Internal tests go in `*_internal_test.go` files
- Use table-driven tests

### Frontend (TypeScript/React)
- Use [prettier](https://prettier.io/) for formatting (config: `.prettierrc.yaml`)
- Follow ESLint rules (config: `.eslintrc.yaml`)

### SDK (Python)
- Follow [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- Format with yapf (config: `.style.yapf`)
- Sort imports with isort (config: `.isort.cfg`)
- Type hints required
- Clear docstrings required

## Key Principles

From `.github/copilot-instructions.md`, code should adhere to:

**SOLID Principles**:
- Single Responsibility Principle
- Open/Closed Principle
- Liskov Substitution Principle
- Interface Segregation Principle
- Dependency Inversion Principle

**Development Principles**:
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- YAGNI (You Aren't Gonna Need It)
- Composition Over Inheritance
- Law of Demeter (Principle of Least Knowledge)
- Separation of Concerns
- High Cohesion, Low Coupling

**Code Quality**:
- Functions must have clear docstrings
- Type hints required for Python
- Complex logic needs comments explaining "why"
- Properly sized, decomposed functions
- New logic requires unit tests
- Large changes need integration/E2E tests

## Important File Locations

- Backend API server: `backend/src/apiserver/`
  - Resource Manager: `backend/src/apiserver/resource/resource_manager.go` (run lifecycle orchestration)
  - Storage layer: `backend/src/apiserver/storage/` (DB operations)
  - Model definitions: `backend/src/apiserver/model/` (GORM models)
- Backend v2 runtime: `backend/src/v2/`
- Frontend React app: `frontend/src/`
- Frontend server: `frontend/server/`
- SDK: `sdk/python/kfp/`
- API protos: `api/v2alpha1/` and `backend/api/v2beta1/`
- Kubernetes platform: `kubernetes_platform/`
- Manifests: `manifests/kustomize/`
- Tests: `test/`, `backend/test/`
- CI workflows: `.github/workflows/`
- Design proposals: `proposals/` (KEP documents for major features)

## Common Development Patterns

### Adding Plugin Input Validation

When adding new plugin input schemas:

1. Define struct with JSON tags (use `omitempty` for optional fields):
   ```go
   type MyPluginInput struct {
       Field1 string `json:"field1,omitempty"`
       Field2 int    `json:"field2,omitempty"`
   }
   ```

2. Use `decoder.DisallowUnknownFields()` for strict validation:
   ```go
   decoder := json.NewDecoder(bytes.NewReader(rawJSON))
   decoder.DisallowUnknownFields()
   input := &MyPluginInput{}
   if err := decoder.Decode(input); err != nil {
       return nil, util.NewInvalidInputError("invalid plugin input: %v", err)
   }
   ```

3. Validate no trailing JSON data:
   ```go
   var trailing json.RawMessage
   if err := decoder.Decode(&trailing); err != io.EOF {
       return nil, util.NewInvalidInputError("plugin input must be a single JSON object")
   }
   ```

### Handling Nullable Database Fields

Use pointers for nullable fields in GORM models:

```go
// Model definition
type RunDetails struct {
    PluginsInputString  *LargeText `gorm:"column:PluginsInput; default:null;"`
    PluginsOutputString *LargeText `gorm:"column:PluginsOutput; default:null;"`
}

// In storage layer (run_store.go)
var pluginsInput sql.NullString
rows.Scan(&uuid, &displayName, ..., &pluginsInput, ...)

if pluginsInput.Valid {
    lt := model.LargeText(pluginsInput.String)
    run.PluginsInputString = &lt
}

// When persisting
SetMap(sq.Eq{
    "PluginsInput": largeTextToNullableSQL(run.PluginsInputString),
})
```

### Error Handling in ResourceManager

Follow the graceful degradation pattern for non-critical features:

```go
// Example: Plugin failures shouldn't block run creation
pluginOutput, pluginErr := handler.OnRunStart(ctx, run, namespace)
if pluginErr != nil {
    glog.Warningf("Plugin OnRunStart failed (run creation will continue): %v", pluginErr)
}
if pluginOutput != nil {
    if err := UpsertRunPluginOutput(run, "plugin-name", pluginOutput); err != nil {
        glog.Warningf("Failed to persist plugin output: %v", err)
    }
}
// Continue with run creation regardless of plugin errors
```

### Reading Kubernetes Resources

When reading ConfigMaps or Secrets in ResourceManager:

```go
clientSet := r.k8sCoreClient.GetClientSet()
if clientSet == nil {
    return nil, util.NewInternalServerError(errors.New("clientset is nil"), "...")
}

cm, err := clientSet.CoreV1().ConfigMaps(namespace).Get(ctx, name, v1.GetOptions{})
if err != nil {
    if apierrors.IsNotFound(err) {
        return nil, nil  // Not found is OK for optional resources
    }
    return nil, util.NewInternalServerError(err, "failed to read configmap")
}
```

## Local Development Tips

**VSCode Debug Configuration** for API server (add to `.vscode/launch.json`):
```json
{
  "name": "Launch API Server (Kind)",
  "type": "go",
  "request": "launch",
  "mode": "debug",
  "program": "${workspaceFolder}/backend/src/apiserver",
  "env": {
    "POD_NAMESPACE": "kubeflow",
    "DBCONFIG_MYSQLCONFIG_HOST": "localhost",
    "OBJECTSTORECONFIG_HOST": "localhost",
    "OBJECTSTORECONFIG_PORT": "9000",
    "METADATA_GRPC_SERVICE_SERVICE_HOST": "localhost",
    "METADATA_GRPC_SERVICE_SERVICE_PORT": "8080",
    "ML_PIPELINE_VISUALIZATIONSERVER_SERVICE_HOST": "localhost",
    "ML_PIPELINE_VISUALIZATIONSERVER_SERVICE_PORT": "8888",
    "V2_LAUNCHER_IMAGE": "ghcr.io/kubeflow/kfp-launcher:master",
    "V2_DRIVER_IMAGE": "ghcr.io/kubeflow/kfp-driver:master"
  },
  "args": ["--config", "${workspaceFolder}/backend/src/apiserver/config", "-logtostderr=true"]
}
```

**Port Forwards for Kind Development**:
- API server: `localhost:8888`
- Frontend UI: `localhost:3000`
- MySQL: `localhost:3306`
- MinIO: `localhost:9000`
- Metadata GRPC: `localhost:8080`

## Additional Resources

- Main documentation: https://www.kubeflow.org/docs/components/pipelines/
- API reference: https://www.kubeflow.org/docs/components/pipelines/reference/api/kubeflow-pipeline-api-spec/
- SDK reference: https://kubeflow-pipelines.readthedocs.io/en/stable/
- Design docs: See `proposals/` directory
- Architecture diagram: `docs/sdk/Architecture.md`
