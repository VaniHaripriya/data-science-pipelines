# Pipeline Run Lifecycle Hooks — MLflow Integration

> **Scope**: API server–only changes on this branch.
> Driver, launcher, SDK, and frontend are out of scope for this PR.

---

## 1. What Changed at a High Level

This branch adds **plugin lifecycle hooks** to three existing pipeline-run operations in the KFP API server:

| KFP Operation | MLflow Hook | What Happens in MLflow |
|---|---|---|
| **Create Run** | `OnRunStart` | Create experiment → create parent run → tag → inject env vars |
| **Report Workflow (terminal)** | `OnRunEnd` | Mark parent run FINISHED/FAILED/KILLED → close nested runs |
| **Retry Run** | `HandleRetry` | Reopen parent run (RUNNING) → reopen failed/killed nested runs |

The hooks are **fire-and-forget**: if any MLflow call fails, the KFP run still proceeds normally. The failure is recorded in `plugins_output.mlflow.state = PLUGIN_FAILED` with a `state_message`.

---

## 2. New Proto Fields

Two new map fields were added to the `Run` message in `run.proto`:

```protobuf
// run.proto — Run message
map<string, google.protobuf.Struct> plugins_input  = 19;  // user provides at creation
map<string, PluginOutput>           plugins_output = 20;  // system populates
```

And one field on `RecurringRun`:

```protobuf
// recurring_run.proto — RecurringRun message
map<string, google.protobuf.Struct> plugins_input  = 19;
```

New message types:

```protobuf
enum PluginState {
  PLUGIN_STATE_UNSPECIFIED = 0;
  PLUGIN_SUCCEEDED         = 1;
  PLUGIN_FAILED            = 2;
}

message MetadataValue {
  enum RenderType { RENDER_TYPE_UNSPECIFIED = 0; URL = 1; }
  google.protobuf.Value value        = 1;
  optional RenderType   render_type  = 2;
}

message PluginOutput {
  map<string, MetadataValue> entries = 1;
  PluginState state                  = 2;
  string state_message               = 3;
}
```

---

## 3. Database Layer

Two nullable `LONGTEXT` columns were added via GORM AutoMigrate:

| Table | Column | Go Field |
|---|---|---|
| `run_details` | `PluginsInput` | `RunDetails.PluginsInputString` |
| `run_details` | `PluginsOutput` | `RunDetails.PluginsOutputString` |
| `jobs` | `PluginsInput` | `Job.PluginsInputString` |

These store the JSON-serialized plugin maps. No migration script is needed — GORM auto-creates nullable columns.

---

## 4. File-by-File Walkthrough

### 4.1 API & Proto Layer

| File | Role |
|---|---|
| `backend/api/v2beta1/run.proto` | Defines `plugins_input`, `plugins_output`, `PluginOutput`, `MetadataValue`, `PluginState` |
| `backend/api/v2beta1/recurring_run.proto` | Defines `plugins_input` on `RecurringRun` |
| `backend/src/apiserver/server/api_converter.go` | Converts between API protos ↔ model structs (JSON serialization/deserialization of plugin maps) |
| `backend/src/apiserver/model/run.go` | `PluginsInputString`, `PluginsOutputString` fields on `RunDetails` |
| `backend/src/apiserver/model/job.go` | `PluginsInputString` field on `Job` |

### 4.2 MLflow Plugin Package (`backend/src/apiserver/mlflow/`)

| File | Role |
|---|---|
| `config.go` | API server–specific configuration: global config (Viper) → namespace config (ConfigMap) → merge → resolve auth → build request context. Type aliases and constant re-exports from `common/mlflow`. |
| `handler.go` | `PluginHandler` interface (run-level only: `OnRunStart`, `OnRunEnd`) + `Handler` struct implementing `OnRunStart`, `OnRunEnd`, `HandleRetry` |
| `run_start.go` | MLflow API interaction helpers: `EnsureExperimentExists`, `CreateExperiment`, `TagRunWithKFPMetadata`, `BuildKFPRunURL`, `BuildRunURL`, `SyncParentAndNestedRuns`, `UpsertRunPluginOutput`, `ModelToPluginRun`, `SyncPluginOutputToModel` |

### 4.3 Shared MLflow Package (`backend/src/common/mlflow/`)

| File | Role |
|---|---|
| `client.go` | Generic Go HTTP client for MLflow REST API — `GetExperimentByName`, `CreateExperiment`, `CreateRun`, `UpdateRun`, `SetTag`, `SearchRuns`, `LogBatch`. Includes retry (exponential backoff) and error helpers (`IsNotFoundError`, `IsAlreadyExistsError`). |
| `config.go` | Shared constants (`DefaultExperimentName`, `EnvTrackingURI`, `EnvWorkspace`, `EnvParentRunID`, `EnvAuthType`), types (`PluginConfig`, `TLSConfig`, `PluginSettings`, `CredentialSecretRef`, `AuthMaterial`), and utility functions (`MergePluginConfig`, `ParsePluginSettings`, `BuildHTTPClient`, `ToMLflowTerminalStatus`). Used by both the API server and (in future PRs) the driver and launcher. |
| `handler.go` | `TaskPluginHandler` interface (`OnTaskStart`, `OnTaskEnd`) and placeholder types (`TaskInfo`, `TaskStartResult`) for future driver/launcher integration. Not used by the API server. |

### 4.4 Orchestration Layer (`backend/src/apiserver/resource/resource_manager.go`)

This is where the hooks are wired into the existing KFP lifecycle:

| Method | Hook Called |
|---|---|
| `CreateRun()` | `applyMLflowOnRunStart()` — called **before** workflow creation to ensure env vars are present on the persisted workflow |
| `ReportWorkflowResource()` | `applyMLflowOnRunEnd()` |
| `RetryRun()` | `applyMLflowOnRunRetry()` |

Common setup/teardown for `OnRunEnd` and `HandleRetry` is factored into `applyMLflowPostAction()`.

### 4.5 Env Var Injection (`backend/src/common/util/workflow.go`)

| Method | Role |
|---|---|
| `SetEnvVarsToDriverAndLauncherTemplates()` | Appends env vars (`KFP_MLFLOW_TRACKING_URI`, `KFP_MLFLOW_WORKSPACE`, `KFP_MLFLOW_PARENT_RUN_ID`, `KFP_MLFLOW_AUTH_TYPE`) to every container and init container in the Argo Workflow spec. This is a post-compilation mutation because MLflow env vars are run-specific and only known after the MLflow parent run is created. |

### 4.6 Recurring Run Propagation

| File | Role |
|---|---|
| `backend/src/crd/pkg/apis/scheduledworkflow/v1beta1/types.go` | `PluginsInput` field on `ScheduledWorkflowSpec` |
| `backend/src/crd/controller/scheduledworkflow/controller.go` | Reads `swf.Spec.PluginsInput` and sets it on triggered `CreateRun` requests |

---

## 5. End-to-End Flow: Create Run

```
User                API Server                    MLflow Server
 │                      │                              │
 │  POST /runs          │                              │
 │  {plugins_input:     │                              │
 │    {mlflow:          │                              │
 │      {experiment_    │                              │
 │       name: "X"}}}   │                              │
 │─────────────────────>│                              │
 │                      │                              │
 │              ┌───────┴───────┐                      │
 │              │ 1. Parse      │                      │
 │              │    plugins_   │                      │
 │              │    input      │                      │
 │              │ (config.go    │                      │
 │              │  Resolve-     │                      │
 │              │  PluginInput) │                      │
 │              └───────┬───────┘                      │
 │                      │                              │
 │              ┌───────┴───────┐                      │
 │              │ 2. Resolve    │                      │
 │              │    config     │                      │
 │              │ (global +     │                      │
 │              │  namespace    │                      │
 │              │  merge)       │                      │
 │              └───────┬───────┘                      │
 │                      │                              │
 │              ┌───────┴───────┐                      │
 │              │ 3. Build HTTP │                      │
 │              │    client     │                      │
 │              │ (auth, TLS,   │                      │
 │              │  retry)       │                      │
 │              └───────┬───────┘                      │
 │                      │                              │
 │                      │  GET /experiments/get-by-name │
 │                      │─────────────────────────────>│
 │                      │<─────────────────────────────│
 │                      │  (or POST /experiments/create)│
 │                      │─────────────────────────────>│
 │                      │<─────────────────────────────│
 │                      │                              │
 │                      │  POST /runs/create           │
 │                      │─────────────────────────────>│
 │                      │<────── run_id ───────────────│
 │                      │                              │
 │                      │  POST /runs/set-tag (×4)     │
 │                      │─────────────────────────────>│
 │                      │<─────────────────────────────│
 │                      │                              │
 │              ┌───────┴───────┐                      │
 │              │ 4. Populate   │                      │
 │              │    plugins_   │                      │
 │              │    output     │                      │
 │              │ {mlflow:      │                      │
 │              │  experiment_  │                      │
 │              │  id, root_    │                      │
 │              │  run_id,      │                      │
 │              │  run_url,     │                      │
 │              │  state:       │                      │
 │              │  SUCCEEDED}   │                      │
 │              └───────┬───────┘                      │
 │                      │                              │
 │              ┌───────┴───────┐                      │
 │              │ 5. Inject env │                      │
 │              │    vars into  │                      │
 │              │    Argo WF    │                      │
 │              │    templates  │                      │
 │              └───────┬───────┘                      │
 │                      │                              │
 │              ┌───────┴───────┐                      │
 │              │ 6. Submit     │                      │
 │              │    workflow   │                      │
 │              │    to K8s     │                      │
 │              └───────┬───────┘                      │
 │                      │                              │
 │              ┌───────┴───────┐                      │
 │              │ 7. Persist    │                      │
 │              │    run + both │                      │
 │              │    plugin     │                      │
 │              │    columns    │                      │
 │              │    to MySQL   │                      │
 │              └───────┬───────┘                      │
 │                      │                              │
 │  <── 200 OK ─────────│                              │
 │  (run with           │                              │
 │   plugins_output)    │                              │
```

> **Note**: Steps 4–5 (MLflow hooks + env var injection) happen **before** step 6 (workflow submission), ensuring the env vars are present on the workflow when it is created in Kubernetes.

---

## 6. End-to-End Flow: Terminal State (OnRunEnd)

```
Persistence Agent          API Server                    MLflow Server
 │                             │                              │
 │  ReportWorkflowResource()  │                              │
 │  (workflow in final state)  │                              │
 │────────────────────────────>│                              │
 │                             │                              │
 │                 ┌───────────┴──────────┐                   │
 │                 │ 1. Read plugins_     │                   │
 │                 │    output from DB    │                   │
 │                 │    (has root_run_id?)│                   │
 │                 └───────────┬──────────┘                   │
 │                             │                              │
 │                             │  POST /runs/update           │
 │                             │  {run_id, status: FINISHED}  │
 │                             │─────────────────────────────>│
 │                             │<─────────────────────────────│
 │                             │                              │
 │                             │  POST /runs/search           │
 │                             │  (find nested runs)          │
 │                             │─────────────────────────────>│
 │                             │<─────────────────────────────│
 │                             │                              │
 │                             │  POST /runs/update (×N)      │
 │                             │  (close active nested runs)  │
 │                             │─────────────────────────────>│
 │                             │<─────────────────────────────│
 │                             │                              │
 │                 ┌───────────┴──────────┐                   │
 │                 │ 2. Update            │                   │
 │                 │    plugins_output    │                   │
 │                 │    .state →          │                   │
 │                 │    PLUGIN_SUCCEEDED  │                   │
 │                 │ 3. Persist to DB     │                   │
 │                 └───────────┬──────────┘                   │
```

---

## 7. End-to-End Flow: Retry (HandleRetry)

```
User                   API Server                    MLflow Server
 │                         │                              │
 │  POST /runs/{id}/retry  │                              │
 │────────────────────────>│                              │
 │                         │                              │
 │             ┌───────────┴──────────┐                   │
 │             │ 1. Read existing     │                   │
 │             │    plugins_output    │                   │
 │             │    (get root_run_id) │                   │
 │             └───────────┬──────────┘                   │
 │                         │                              │
 │                         │  POST /runs/update           │
 │                         │  {run_id, status: RUNNING}   │
 │                         │─────────────────────────────>│
 │                         │<─────────────────────────────│
 │                         │                              │
 │                         │  POST /runs/search           │
 │                         │  (find failed/killed nested) │
 │                         │─────────────────────────────>│
 │                         │<─────────────────────────────│
 │                         │                              │
 │                         │  POST /runs/update (×N)      │
 │                         │  (reopen nested → RUNNING)   │
 │                         │─────────────────────────────>│
 │                         │<─────────────────────────────│
 │                         │                              │
 │             ┌───────────┴──────────┐                   │
 │             │ 2. Update            │                   │
 │             │    plugins_output    │                   │
 │             │    .state →          │                   │
 │             │    PLUGIN_SUCCEEDED  │                   │
 │             │ 3. Persist to DB     │                   │
 │             └───────────┬──────────┘                   │
 │                         │                              │
 │  <── 200 OK ────────────│                              │
```

---

## 8. Configuration Resolution

Configuration is resolved in this priority order (namespace overrides global). Either global or namespace config alone is sufficient to enable MLflow.

```
┌──────────────────────────┐     ┌───────────────────────────┐
│   Global Config          │     │  Namespace Config          │
│   (Viper / config.json)  │     │  (kfp-launcher ConfigMap)  │
│                          │     │                           │
│   plugins.mlflow:        │     │  plugins.mlflow:          │
│     endpoint: http://... │     │    endpoint: (override)   │
│     timeout: 30s         │     │    settings:              │
│     settings:            │     │      authType: bearer     │
│       authType: none     │     │      credentialSecretRef: │
│       workspacesEnabled: │     │        name: my-secret    │
│         false            │     │                           │
└──────────┬───────────────┘     └─────────┬─────────────────┘
           │                               │
           └───────────┬───────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Merged Config │
              │  (namespace    │
              │   wins on      │
              │   conflicts)   │
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │ Parse Settings │
              │ Resolve Auth   │
              │ Build HTTP     │
              │ Client         │
              └────────────────┘
```

### Auth Types

| Auth Type | How Credentials Are Obtained |
|---|---|
| `none` | No credentials (local dev) |
| `kubernetes` (default) | Service account token from `/var/run/secrets/...` |
| `bearer` | Token from a Kubernetes Secret (via `credentialSecretRef`) |
| `basic-auth` | Username/password from a Kubernetes Secret |

---

## 9. Environment Variables Injected into Workflows

When `OnRunStart` succeeds, these env vars are added to **every container and init container** in the Argo Workflow:

| Env Var | Value |
|---|---|
| `KFP_MLFLOW_TRACKING_URI` | MLflow endpoint URL (e.g., `http://mlflow:5000`) |
| `KFP_MLFLOW_WORKSPACE` | Kubernetes namespace |
| `KFP_MLFLOW_PARENT_RUN_ID` | MLflow parent run ID |
| `KFP_MLFLOW_AUTH_TYPE` | Auth type used (`none`, `kubernetes`, `bearer`, `basic-auth`) |

These are consumed by the driver and launcher (in future PRs) to create **nested MLflow runs** for individual tasks.

---

## 10. MLflow Tags Set on the Parent Run

| Tag Key | Value |
|---|---|
| `kfp.pipeline_run_id` | KFP run UUID |
| `kfp.pipeline_run_url` | `/#/runs/details/<run_id>` (relative path) |
| `kfp.pipeline_id` | Pipeline ID (if present) |
| `kfp.pipeline_version_id` | Pipeline version ID (if present) |

---

## 11. Plugin Output Stored in the Database

After `OnRunStart`, the `plugins_output` column in the `run_details` table contains:

```json
{
  "mlflow": {
    "entries": {
      "experiment_name": { "value": "my-experiment" },
      "experiment_id":   { "value": "1" },
      "root_run_id":     { "value": "abc123..." },
      "run_url":         { "value": "http://mlflow:5000/experiments/1/runs/abc123...", "renderType": "URL" }
    },
    "state": "PLUGIN_SUCCEEDED",
    "stateMessage": ""
  }
}
```

After `OnRunEnd` or `HandleRetry`, only `state` and `stateMessage` change. The `entries` remain the same.

---

## 12. Graceful Degradation

Every MLflow hook is wrapped in error handling that ensures the KFP run is **never blocked**:

```go
// resource_manager.go — applyMLflowOnRunStart
pluginOutput, pluginErr := handler.OnRunStart(ctx, apiRun, resolvedCfg.Config)
if pluginErr != nil {
    glog.Warningf("MLflow OnRunStart failed for run %q (run creation will continue): %v",
        run.UUID, pluginErr)
}
```

If MLflow is unreachable or returns an error:
- **Create Run**: Run is still created. `plugins_output.mlflow.state = PLUGIN_FAILED`.
- **Terminal State**: Run state is persisted normally. Plugin output records the failure.
- **Retry**: Retry proceeds. Plugin output records the failure.

---

## 13. Code Organization

The MLflow code is split across two Go packages to separate API server–specific logic from shared code:

| Package | Purpose | Used By |
|---|---|---|
| `backend/src/common/mlflow` | Shared constants, types, HTTP client, and utility functions. No Kubernetes client dependency. | API server now; driver and launcher in future PRs |
| `backend/src/apiserver/mlflow` | API server–specific plugin hooks, configuration resolution (Viper, ConfigMap, Secrets, auth), and orchestration helpers. Depends on Kubernetes client. | API server only |

The `apiserver/mlflow` package re-exports shared types via type aliases (e.g., `type PluginConfig = commonmlflow.PluginConfig`) so callers within the API server use a single import.

### Interface Split

| Interface | Package | Methods | Implementor |
|---|---|---|---|
| `PluginHandler` | `apiserver/mlflow` | `OnRunStart`, `OnRunEnd` | `Handler` (API server) |
| `TaskPluginHandler` | `common/mlflow` | `OnTaskStart`, `OnTaskEnd` | Future driver/launcher handler |

The `PluginHandler` interface covers run-level hooks only. Task-level hooks (`OnTaskStart`, `OnTaskEnd`) are defined in `common/mlflow` for future driver/launcher use and are **not** called by the API server.

---

## 14. What This Branch Does NOT Do

| Aspect | Status |
|---|---|
| Delete MLflow runs when KFP run is deleted | Not implemented (design decision — orphan runs in MLflow) |
| Driver-level nested run creation | Env vars are injected; driver code changes are a future PR |
| Launcher-level metrics/artifact logging | Env vars are injected; launcher code changes are a future PR |
| SDK changes | Not in scope for this PR |
| Frontend UI for `plugins_output` | Not in scope for this PR (visible only via REST API) |
| `secretKeyRef` credential mounting on workflow templates | Pending driver/launcher follow-up |
| `CloneRun` propagation of `plugins_input` | Follow-up task |

---

## 15. Key Design Decisions

1. **API server is the only Kubernetes client user**: Only the API server reads ConfigMaps, Secrets, and performs credential resolution. The driver and launcher will use only the env vars injected at workflow creation time plus direct HTTP calls to MLflow.

2. **Relative KFP run URLs**: The `kfp.pipeline_run_url` tag is always a relative path (`/#/runs/details/<id>`), avoiding the need for a base URL configuration.

3. **Race-safe experiment creation**: `EnsureExperimentExists` handles the race condition where two concurrent runs try to create the same MLflow experiment by catching `RESOURCE_ALREADY_EXISTS` and falling back to a `GetByName`.

4. **Self-contained persistence in OnRunEnd/HandleRetry**: These hooks persist `plugins_output` via `UpdateRunPluginsOutput` independently, so the caller's `UpdateRun` call doesn't need to include plugin fields.

5. **Plugin state is separate from run state**: `PLUGIN_SUCCEEDED` / `PLUGIN_FAILED` reflects whether the MLflow API calls succeeded, not whether the pipeline run itself succeeded.

6. **Namespace-only enablement**: MLflow can be enabled via namespace config alone (kfp-launcher ConfigMap) without requiring global config in Viper. Either source is sufficient.

7. **Env vars injected before workflow submission**: `applyMLflowOnRunStart` runs before `workflowClient.Create()` to ensure the env vars are present on the workflow templates when submitted to Kubernetes.

8. **Shared `applyMLflowPostAction` helper**: `OnRunEnd` and `HandleRetry` share common config-resolution and output-persistence logic via a single helper in `resource_manager.go`, reducing duplication.
