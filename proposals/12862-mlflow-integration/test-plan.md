# KEP-12862: MLflow Integration — Test Plan

**Feature**: Pipeline Run Lifecycle Hooks for MLflow Integration  
**Branch**: `pipeline-run-api-hooks`  
**Design Doc**: [KEP-12862 README](./README.md)  
**Last Updated**: 2026-03-18  

---

## 1. Scope & Objectives

This test plan covers all changes introduced by the `pipeline-run-api-hooks` branch, which adds:

1. **Proto changes** — `plugins_input` / `plugins_output` fields on `Run` (fields 19, 20) and `RecurringRun` (field 19), plus new `PluginOutput`, `MetadataValue`, and `PluginState` messages.
2. **API server MLflow handler** — `OnRunStart`, `OnRunEnd`, `HandleRetry` run-level lifecycle hooks in `backend/src/apiserver/mlflow/handler.go`.
3. **MLflow config resolution** — Global (Viper) + namespace (ConfigMap) config merge, auth credential resolution (`kubernetes`, `bearer`, `basic-auth`) in `backend/src/apiserver/mlflow/config.go`.
4. **MLflow helpers** — Experiment creation, run tagging, parent/nested run sync, plugin output serialization in `backend/src/apiserver/mlflow/run_start.go`.
5. **Shared MLflow Go HTTP client** — `backend/src/common/mlflow/client.go` with `GetExperimentByName`, `CreateExperiment`, `CreateRun`, `UpdateRun`, `SetTag`, `SearchRuns`, retry with exponential backoff.
6. **Shared MLflow types** — `backend/src/common/mlflow/config.go` (`PluginConfig`, `PluginSettings`, `MLflowCredentials`, `MLflowRuntimeConfig`, `MergePluginConfig`, `ParsePluginSettings`, `BuildHTTPClient`, `ToMLflowTerminalStatus`).
7. **Task-level handler interface** — `backend/src/common/mlflow/handler.go` (`TaskPluginHandler`, `TaskInfo`, `TaskStartResult` — stubs for future driver/launcher work).
8. **Env var injection** — Single `KFP_MLFLOW_CONFIG` JSON env var and `--mlflow_enabled` CLI flag injected into Argo Workflow templates via `backend/src/common/util/workflow.go`.
9. **Resource manager integration** — `applyMLflowOnRunStart` (before workflow create), `applyMLflowOnRunEnd` (on terminal), `applyMLflowOnRunRetry` in `backend/src/apiserver/resource/resource_manager.go`.
10. **ScheduledWorkflow CRD extension** — `PluginsInput` field on `ScheduledWorkflowSpec`; SWF controller propagates it to each triggered `CreateRun` call.
11. **API converter & validation** — Serialization/deserialization, payload limit validation, model↔API conversion for plugin fields in `backend/src/apiserver/server/api_converter.go`.
12. **Storage layer** — `PluginsInputString` and `PluginsOutputString` columns on `run_details` and `jobs` tables; `UpdateRunPluginsOutput` method.
13. **Plugin limits config** — Configurable `MaxKeys`, `MaxPayloadBytes`, `MaxTotalPayloadBytes`, `MaxNestingDepth` in `backend/src/apiserver/common/`.
14. **Auto-migration** — Centralized `AllModels()` in `backend/src/apiserver/model/common.go`; GORM `AutoMigrate` adds new nullable columns.
15. **Template** — `v2_template.go` propagates `PluginsInput` to `ScheduledWorkflowSpec`.
16. **Proto test goldens** — Updated `run_completed.json`, `run_failed.json`, `recurring_run.json` etc. under `backend/test/proto_tests/testdata/`.

### Out of Scope (for this PR)

- Driver / Launcher MLflow integration (task-level hooks — `OnTaskStart`, `OnTaskEnd` are defined but not implemented).
- SDK changes (`plugins_input` parameter on client methods).
- Frontend rendering of `plugins_output`.
- `CloneRun` plugin propagation.
- `secretKeyRef` credential mounting on Argo templates (values are resolved server-side today, not mounted via `valueFrom`).

---

## 2. Changed Files

| # | File | Change Summary |
|---|---|---|
| 1 | `backend/api/v2beta1/run.proto` | Added `plugins_input` (field 19), `plugins_output` (field 20), `PluginOutput`, `MetadataValue`, `PluginState` |
| 2 | `backend/api/v2beta1/recurring_run.proto` | Added `plugins_input` (field 19) |
| 3 | `backend/api/v2beta1/go_client/run.pb.go` | Generated Go code |
| 4 | `backend/api/v2beta1/go_client/recurring_run.pb.go` | Generated Go code |
| 5 | `backend/api/v2beta1/go_http_client/run_model/...` | Generated HTTP model code (4 new files) |
| 6 | `backend/api/v2beta1/go_http_client/recurring_run_model/...` | Generated HTTP model code |
| 7 | `backend/api/v2beta1/python_http_client/...` | Generated Python HTTP client (7 new files, 3 updated) |
| 8 | `backend/api/v2beta1/swagger/...` | Updated Swagger specs (3 files) |
| 9 | `backend/src/apiserver/mlflow/config.go` | API server MLflow config resolution, auth, env var injection |
| 10 | `backend/src/apiserver/mlflow/config_test.go` | 12 unit tests |
| 11 | `backend/src/apiserver/mlflow/handler.go` | `PluginHandler` interface, `Handler` struct, `OnRunStart`, `OnRunEnd`, `HandleRetry` |
| 12 | `backend/src/apiserver/mlflow/handler_test.go` | 19 top-level tests (+ table-driven sub-tests) |
| 13 | `backend/src/apiserver/mlflow/run_start.go` | MLflow experiment/run helpers, plugin output serialization, nested run sync |
| 14 | `backend/src/common/mlflow/client.go` | Shared MLflow REST client (6 API methods + retry) |
| 15 | `backend/src/common/mlflow/config.go` | Shared types, constants, `MergePluginConfig`, `ParsePluginSettings`, `BuildHTTPClient`, `ToMLflowTerminalStatus` |
| 16 | `backend/src/common/mlflow/handler.go` | `TaskPluginHandler` interface, `TaskInfo`, `TaskStartResult` stubs |
| 17 | `backend/src/common/util/workflow.go` | `SetEnvVarsToDriverAndLauncherTemplates`, `SetMLflowEnabledFlag`, `appendEnvNoDuplicates`, `hasArg` |
| 18 | `backend/src/apiserver/resource/resource_manager.go` | `applyMLflowOnRunStart`, `applyMLflowOnRunEnd`, `applyMLflowOnRunRetry`, `applyMLflowPostAction` |
| 19 | `backend/src/apiserver/resource/resource_manager_test.go` | 2 new integration tests |
| 20 | `backend/src/apiserver/server/api_converter.go` | Plugin field serialization, deserialization, validation |
| 21 | `backend/src/apiserver/server/api_converter_test.go` | 15 new unit tests |
| 22 | `backend/src/apiserver/storage/run_store.go` | `UpdateRunPluginsOutput`, plugin field persistence |
| 23 | `backend/src/apiserver/storage/run_store_test.go` | 6 new tests |
| 24 | `backend/src/apiserver/storage/job_store.go` | Job plugin field persistence |
| 25 | `backend/src/apiserver/storage/job_store_test.go` | 1 new test |
| 26 | `backend/src/apiserver/storage/sql_null_util.go` | `largeTextToNullableSQL` helper |
| 27 | `backend/src/apiserver/storage/db_fake.go` | Updated fake DB for plugin columns |
| 28 | `backend/src/apiserver/model/run.go` | `PluginsInputString`, `PluginsOutputString` fields on `RunDetails` |
| 29 | `backend/src/apiserver/model/job.go` | `PluginsInputString` field on `Job` |
| 30 | `backend/src/apiserver/model/common.go` | `AllModels()` for centralized AutoMigrate |
| 31 | `backend/src/apiserver/common/const.go` | Plugin limits defaults |
| 32 | `backend/src/apiserver/common/config.go` | `PluginLimitsConfig`, `GetPluginLimitsConfig()` |
| 33 | `backend/src/apiserver/common/config_test.go` | 6 new tests for plugin limits |
| 34 | `backend/src/apiserver/main.go` | Plugin limits validation at startup and on config change |
| 35 | `backend/src/apiserver/template/v2_template.go` | `PluginsInput` propagation to SWF spec |
| 36 | `backend/src/apiserver/client_manager/client_manager.go` | `AllModels()` for AutoMigrate |
| 37 | `backend/src/apiserver/client_manager/client_manager_test.go` | 1 new test |
| 38 | `backend/src/crd/controller/scheduledworkflow/controller.go` | `parsePluginsInputJSON`, propagation to `CreateRun` |
| 39 | `backend/src/crd/controller/scheduledworkflow/controller_test.go` | 5 sub-tests |
| 40 | `backend/src/crd/pkg/apis/scheduledworkflow/v1beta1/types.go` | `PluginsInput` field on `ScheduledWorkflowSpec` |
| 41 | `backend/test/proto_tests/testdata/generated-1791485/...` | Updated proto golden files (4 files) |

---

## 3. Existing Test Coverage on Branch

| Test File | New Tests | Coverage Focus |
|---|---|---|
| `mlflow/config_test.go` | 12 tests | Config resolution, merging, settings parsing, auth (kubernetes, bearer, basic-auth), experiment ops, plugin output, terminal status |
| `mlflow/handler_test.go` | 19 tests | OnRunStart (nil/disabled/success/failure), OnRunEnd (nil/no-output/missing-root/nil-config/success), HandleRetry (no-output/missing-root/nil-config/success), BuildKFPRunURL, ModelToPluginRun, SyncPluginOutputToModel, SyncParentAndNestedRuns with pagination |
| `server/api_converter_test.go` | 15 tests | JSON↔proto serialization, validation limits, nesting depth, configurable overrides, model↔API round-trip (Run + RecurringRun) |
| `storage/run_store_test.go` | 6 tests | CRUD with plugin fields, NULL handling, UpdateRunPluginsOutput, list with plugins |
| `storage/job_store_test.go` | 1 test | Job CRUD with PluginsInput |
| `resource/resource_manager_test.go` | 2 tests | MLflow OnRunStart in CreateRun, RetryRun MLflow reopening |
| `crd/controller_test.go` | 5 sub-tests | `parsePluginsInputJSON` valid/invalid cases |
| `common/config_test.go` | 6 tests | Plugin limits defaults, overrides, invalid values, overflow, cross-field invariant |
| `client_manager_test.go` | 1 test | AutoMigrate with AllModels() |

**Total new tests: ~67** (top-level test functions + table-driven sub-tests)

---

## 4. Test Plan

### 4.1 Positive Functional Tests

#### 4.1.1 Proto & API Contract

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | `plugins_input` round-trip on Run proto | 1. Create `Run` proto with `plugins_input = {"mlflow": {"experiment_name": "exp-1"}}`<br>2. Serialize to JSON<br>3. Deserialize back | Map preserved with correct structure and values | | Yes — `api_converter_test.go::TestPluginsInputToJSON`, `TestJSONToPluginsInput` |
| **P0** | `plugins_output` round-trip on Run proto | 1. Create `Run` proto with `plugins_output = {"mlflow": {entries: {...}, state: PLUGIN_SUCCEEDED}}`<br>2. Serialize/deserialize | Map preserved with entries, state, state_message | | Yes — `api_converter_test.go::TestPluginsOutputToJSON`, `TestJSONToPluginsOutput` |
| **P0** | `plugins_input` on RecurringRun proto | 1. Create `RecurringRun` proto with `plugins_input`<br>2. Serialize/deserialize | Field preserved on round-trip | | Yes — `api_converter_test.go::TestToModelJobPluginsInput`, `TestToApiRecurringRunPluginsInput` |
| **P1** | `MetadataValue` with `render_type: URL` | 1. Build `PluginOutput` with `run_url` entry having `render_type = URL`<br>2. Serialize and verify | `render_type` preserved as `URL` enum | | Yes — `config_test.go::TestBuildPluginOutput` |
| **P1** | `PluginState` enum coverage | 1. Verify all 4 values: `PLUGIN_STATE_UNSPECIFIED`, `PLUGIN_RUNNING`, `PLUGIN_SUCCEEDED`, `PLUGIN_FAILED` | All values defined and distinct | | Yes — Proto generated code |
| **P1** | Proto backward compatibility (field numbers) | 1. Verify `plugins_input` = field 19, `plugins_output` = field 20<br>2. Verify field 18 (`pipeline_version_reference`) unaffected | No wire-format collisions | | Yes — Proto inspection |
| **P1** | Proto golden file validation | 1. Run proto compatibility tests against `backend/test/proto_tests/testdata/generated-1791485/`<br>2. Verify `run_completed.json`, `run_failed.json`, `recurring_run.json` include `plugins_input: {}` / `plugins_output: {}` | Golden files match updated proto schema | | Yes — Proto test suite |

#### 4.1.2 CreateRun with MLflow Integration

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | CreateRun with default experiment name | 1. Configure global `plugins.mlflow` in API server config<br>2. Call `CreateRun` without `plugins_input`<br>3. Verify MLflow API calls | MLflow experiment "Default" looked up/created; parent run created; `plugins_output.mlflow` populated with `experiment_id`, `root_run_id`, `run_url`; state = `PLUGIN_SUCCEEDED` | | Yes — `handler_test.go::TestOnRunStart_Success` |
| **P0** | CreateRun with custom experiment name | 1. Call `CreateRun` with `plugins_input = {"mlflow": {"experiment_name": "my-exp"}}`<br>2. Verify experiment creation | Experiment "my-exp" looked up/created; parent run under "my-exp" | | Partial — handler test covers; cluster integration test needed |
| **P0** | `experiment_id` takes precedence over `experiment_name` | 1. Provide both `experiment_name` and `experiment_id`<br>2. Call `CreateRun` | `experiment_id` used directly; no name lookup | | Yes — `config_test.go::TestSelectMLflowExperiment` |
| **P0** | `KFP_MLFLOW_CONFIG` env var injection | 1. Call `OnRunStart` successfully<br>2. Verify `handler.RunStartEnv` map<br>3. Verify `InjectMLflowRuntimeEnv` calls `SetEnvVarsToDriverAndLauncherTemplates` | Single `KFP_MLFLOW_CONFIG` JSON env var on all driver containers, init containers | | Yes — `handler_test.go::TestOnRunStart_Success`, `resource_manager_test.go` |
| **P0** | `MLflowRuntimeConfig` JSON payload contents | 1. Marshal `MLflowRuntimeConfig` after successful `OnRunStart`<br>2. Verify JSON fields | JSON contains `endpoint`, `workspace`, `parentRunId`, `experimentId`, `authType`, `timeout`, `insecureSkipVerify` | | Yes — `handler_test.go::TestOnRunStart_Success` (asserts JSON payload) |
| **P0** | `--mlflow_enabled` flag injected | 1. Call `OnRunStart` → sets `MLflowEnabled = true`<br>2. `InjectMLflowRuntimeEnv` calls `SetMLflowEnabledFlag`<br>3. Verify driver containers get `--mlflow_enabled` in Args | Flag appended to containers with `--type` arg (drivers) and `--copy` arg (launcher init) | | Yes — `workflow.go` logic, `resource_manager.go` integration |
| **P0** | Env var injection occurs **before** workflow create | 1. In `CreateRun`, verify `applyMLflowOnRunStart` called before `workflowClient.Create` | Env vars baked into templates before Kubernetes submission | | Yes — `resource_manager.go` call ordering |
| **P1** | MLflow parent run tagged with KFP metadata | 1. Create run with `pipeline_id` and `pipeline_version_id`<br>2. Verify `SetTag` calls | Tags: `kfp.pipeline_run_id`, `kfp.pipeline_run_url`, `kfp.pipeline_id`, `kfp.pipeline_version_id` | | Yes — `config_test.go::TestCreateParentRunAndTagWithKFPMetadata` |
| **P1** | MLflow run URL format | 1. Call `BuildRunURL` with valid `RequestContext`<br>2. Verify URL | `<endpoint>/experiments/<id>/runs/<id>?workspace=<ns>` | | Yes — `handler_test.go::TestBuildKFPRunURL` |
| **P1** | KFP run URL (relative) | 1. Call `BuildKFPRunURL(runID)` | Returns `/#/runs/details/<runID>` | | Yes — `handler_test.go::TestBuildKFPRunURL` |
| **P1** | Experiment description defaults | 1. No `experimentDescription` set → default = "Created by Kubeflow Pipelines"<br>2. Set to `""` → no description applied<br>3. Set to custom → custom used | All three cases handled correctly | | Yes — `run_start.go::ResolveExperimentDescription` logic |
| **P2** | Race-safe experiment creation | 1. Two concurrent `EnsureExperimentExists` calls<br>2. First succeeds, second gets `RESOURCE_ALREADY_EXISTS`<br>3. Second falls back to `GetExperimentByName` | Both succeed without error | | Yes — `run_start.go::CreateExperiment` fallback logic |

#### 4.1.3 GetRun / ListRuns with Plugin Fields

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | GetRun returns `plugins_input` and `plugins_output` | 1. Create `model.Run` with both plugin fields<br>2. Read back from store<br>3. Convert to API Run | Fields preserved end-to-end | | Yes — `run_store_test.go::TestCreateRunWithPluginsFields`, `api_converter_test.go::TestToApiRunPluginsFields` |
| **P0** | ListRuns returns plugin fields | 1. Create multiple runs with plugin data<br>2. Call `ListRuns` | All runs include their plugin fields | | Yes — `run_store_test.go::TestListRunsReturnsPluginsFields` |
| **P1** | Run with NULL plugin fields | 1. Create run without plugin fields<br>2. Read back | `PluginsInputString` and `PluginsOutputString` are nil | | Yes — `run_store_test.go::TestCreateRunWithEmptyPluginsFieldsWritesNull` |

#### 4.1.4 ReportWorkflowResource (Terminal State)

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | SUCCEEDED → MLflow parent FINISHED | 1. Run has MLflow `plugins_output` with `root_run_id`<br>2. Report terminal state = SUCCEEDED<br>3. Verify `UpdateRun` call with "FINISHED" | Parent run marked FINISHED; `plugins_output.mlflow.state` = `PLUGIN_SUCCEEDED` | | Yes — `handler_test.go::TestOnRunEnd_Success` |
| **P0** | FAILED → MLflow parent FAILED | 1. Report terminal state = FAILED | Parent run marked FAILED | | Yes — `config_test.go::TestToMLflowTerminalStatus` + handler test |
| **P0** | CANCELED → MLflow parent KILLED | 1. Report terminal state = CANCELED | Parent run marked KILLED | | Yes — `config_test.go::TestToMLflowTerminalStatus` |
| **P1** | Nested runs closed on terminal | 1. Parent has active nested runs (RUNNING/SCHEDULED)<br>2. Report terminal state<br>3. Verify `SearchRuns` + `UpdateRun` for each | All RUNNING/SCHEDULED nested runs updated to terminal status | | Yes — `handler_test.go::TestSyncParentAndNestedRuns_Pagination` |
| **P1** | Pagination in nested run search | 1. MLflow returns multiple pages of nested runs<br>2. Verify all pages processed | All nested runs across pages updated | | Yes — `handler_test.go::TestSyncParentAndNestedRuns_Pagination` |
| **P1** | `plugins_output` persisted after terminal sync | 1. `OnRunEnd` updates plugin output state<br>2. `SyncPluginOutputToModel` writes back to `model.Run`<br>3. `UpdateRunPluginsOutput` persists to DB | State persisted correctly | | Yes — `resource_manager.go::applyMLflowPostAction` + `run_store_test.go::TestUpdateRunPluginsOutputOnly` |

#### 4.1.5 RetryRun

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | RetryRun reopens MLflow parent run | 1. Failed run with MLflow `plugins_output`<br>2. Call `RetryRun`<br>3. Verify `UpdateRun(parentRunID, "RUNNING", nil)` | Parent run set to RUNNING; `plugins_output.mlflow.state` = `PLUGIN_SUCCEEDED` | | Yes — `handler_test.go::TestHandleRetry_Success`, `resource_manager_test.go::TestRetryRun_ReopensMLflowParentAndFailedNestedRuns` |
| **P0** | RetryRun only reopens FAILED/KILLED nested runs | 1. Nested runs in FAILED, KILLED, FINISHED states<br>2. Call RetryRun | Only FAILED and KILLED reopened; FINISHED left alone | | Yes — `run_start.go::shouldSyncNestedRun`, `resource_manager_test.go` |
| **P1** | RetryRun with no `plugins_output` is no-op | 1. Failed run without MLflow<br>2. Call RetryRun | No MLflow API calls; no errors | | Yes — `handler_test.go::TestHandleRetry_NoPluginOutput_NoOp` |

#### 4.1.6 Recurring Runs

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | CreateJob with `plugins_input` | 1. Create recurring run with `plugins_input = {"mlflow": {"experiment_name": "recurring-exp"}}`<br>2. Verify model `PluginsInputString` | `PluginsInputString` populated on `Job` model | | Yes — `job_store_test.go::TestCreateJobPluginsInput` |
| **P0** | SWF template propagates `PluginsInput` | 1. Model Job has `PluginsInputString`<br>2. `NewGenericScheduledWorkflow` builds SWF spec<br>3. Verify `PluginsInput` field on SWF spec | `PluginsInput` set on `ScheduledWorkflowSpec` | | Yes — `v2_template.go` logic |
| **P0** | SWF controller propagates `plugins_input` to triggered run | 1. SWF spec has `PluginsInput`<br>2. Controller parses via `parsePluginsInputJSON`<br>3. `CreateRun` includes `plugins_input` | Each triggered run inherits `plugins_input` from recurring run | | Yes — `controller_test.go::TestParsePluginsInputJSON` (5 sub-tests) |
| **P1** | RecurringRun API round-trip | 1. Create recurring run with `plugins_input`<br>2. Retrieve via API<br>3. Verify preserved | Full round-trip preserves `plugins_input` | | Yes — `api_converter_test.go::TestToModelJobPluginsInput`, `TestToApiRecurringRunPluginsInput` |

#### 4.1.7 MLflow Configuration

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | Global config resolution | 1. Set `plugins.mlflow` in Viper config<br>2. Call `GetGlobalMLflowConfig` | Returns valid `PluginConfig` with endpoint, timeout, settings | | Yes — `config_test.go::TestGetGlobalMLflowConfig` |
| **P0** | `kubernetes` auth type reads SA token | 1. Set `authType: "kubernetes"`<br>2. Call `ResolveMLflowCredentials` | Bearer token read from `ServiceAccountTokenPath` | | Yes — `config_test.go::TestBuildMLflowRequestContextKubernetesAuth` |
| **P0** | `bearer` auth type reads from Secret | 1. Set `authType: "bearer"` with `credentialSecretRef`<br>2. Call `ResolveMLflowCredentials` | Token read from referenced Secret key | | Yes — `config_test.go::TestBuildMLflowRequestContextSecretBasedAuth` (bearer sub-test) |
| **P0** | `basic-auth` type reads from Secret | 1. Set `authType: "basic-auth"` with `credentialSecretRef`<br>2. Call `ResolveMLflowCredentials` | Username + password read from Secret | | Yes — `config_test.go::TestBuildMLflowRequestContextSecretBasedAuth` (basic-auth sub-test) |
| **P1** | Namespace config merges with global | 1. Set global endpoint A<br>2. Set namespace ConfigMap with endpoint B<br>3. Call `ResolveMLflowRequestConfig` | Endpoint = B; timeout inherited from global | | Yes — `config_test.go::TestMergePluginConfigAndSettingsDefaults` |
| **P1** | Namespace-only enablement (no global) | 1. No global `plugins.mlflow`<br>2. Set namespace ConfigMap with `plugins.mlflow`<br>3. Call `ResolveMLflowRequestConfig` | Returns merged config from namespace only (`hasGlobal=false, hasNamespace=true` branch) | | Partial — logic implemented, needs explicit test |
| **P1** | Namespace endpoint override requires credentials | 1. Namespace overrides endpoint but no `credentialSecretRef`<br>2. Resolve config | Error: "namespace plugins.mlflow endpoint override requires namespace credentialSecretRef" | | Yes — `config.go` validation logic |
| **P2** | `WorkspacesEnabled` defaults | 1. `kubernetes` auth → `workspacesEnabled = true`<br>2. `bearer` auth → `workspacesEnabled = false` | Correct defaults applied | | Yes — `config_test.go::TestMergePluginConfigAndSettingsDefaults` |

#### 4.1.8 MLflow Go HTTP Client

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | `GetExperimentByName` | 1. Mock MLflow server<br>2. Call `GetExperimentByName("exp")`<br>3. Verify HTTP GET, query params, headers | Correct request; response parsed | | Yes — `config_test.go::TestEnsureExperimentExists` (via handler integration) |
| **P0** | `CreateExperiment` with description | 1. Mock MLflow<br>2. Call `CreateExperiment` with name + description<br>3. Verify POST body | Body includes `name` and `description` fields | | Yes — `config_test.go::TestEnsureExperimentExists` |
| **P0** | `CreateRun` | 1. Mock MLflow<br>2. Call `CreateRun(experimentID, runName, nil)` | Correct POST; `run_id` extracted from response | | Yes — `config_test.go::TestCreateParentRunAndTagWithKFPMetadata` |
| **P0** | `UpdateRun` with status and end_time | 1. Call `UpdateRun(runID, "FINISHED", &endTime)` | Correct POST body with `run_id`, `status`, `end_time` | | Yes — `handler_test.go::TestOnRunEnd_Success` (via mock verification) |
| **P0** | `SetTag` | 1. Call `SetTag(runID, key, value)` | Correct POST body | | Yes — `config_test.go::TestCreateParentRunAndTagWithKFPMetadata` |
| **P0** | `SearchRuns` with pagination | 1. Mock paginated responses<br>2. Call `SearchRuns` | Pagination token followed; all runs returned | | Yes — `handler_test.go::TestSyncParentAndNestedRuns_Pagination` |
| **P1** | `X-MLflow-Workspace` header | 1. Enable workspaces<br>2. Make any API call<br>3. Verify header | `X-MLflow-Workspace: <namespace>` present | | Yes — `config_test.go` (asserts header) |
| **P1** | 4xx errors are permanent (no retry) | 1. Mock 400 response<br>2. Verify no retry | `backoff.Permanent` error returned immediately | | Yes — `client.go::doWithRetry` logic |
| **P1** | 5xx errors trigger retry | 1. Mock 500 then 200<br>2. Verify retry succeeds | Request retried; success on second attempt | | Partial — backoff logic present, needs explicit test |

#### 4.1.9 API Converter & Validation

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | `PluginsInputToJSON` | 1. Convert `map[string]*structpb.Struct` to JSON string | Valid JSON string | | Yes — `api_converter_test.go::TestPluginsInputToJSON` |
| **P0** | `JSONToPluginsInput` | 1. Convert JSON to protobuf map | Correct structure | | Yes — `api_converter_test.go::TestJSONToPluginsInput` |
| **P0** | `PluginsOutputToJSON` | 1. Convert `map[string]*PluginOutput` to JSON | Valid JSON with entries/state | | Yes — `api_converter_test.go::TestPluginsOutputToJSON` |
| **P0** | `JSONToPluginsOutput` | 1. Convert JSON to proto map | Correct deserialization | | Yes — `api_converter_test.go::TestJSONToPluginsOutput` |
| **P0** | `ValidatePluginsOutput` | 1. Validate well-formed output | No error | | Yes — `api_converter_test.go::TestValidatePluginsOutput` |
| **P0** | `ValidatePluginsInputLimits` | 1. Send payload exceeding `MaxTotalPayloadBytes`<br>2. Verify error | Limit violation error | | Yes — `api_converter_test.go::TestValidatePluginsInputLimits` |
| **P0** | `ValidatePluginsOutputLimits` | 1. Same for output | Limit violation error | | Yes — `api_converter_test.go::TestValidatePluginsOutputLimits` |
| **P1** | Configurable limit overrides | 1. Set custom limits via Viper<br>2. Validate | Custom limits respected | | Yes — `TestValidatePluginsInputLimitsUsesConfiguredOverrides`, `TestValidatePluginsOutputLimitsUsesConfiguredOverrides` |
| **P1** | Nesting depth validation | 1. Deeply nested JSON | Depth error | | Yes — `TestValidatePluginsInputLimitsUsesNestingDepthOverride` |
| **P1** | Total payload size override | 1. Override total payload bytes<br>2. Validate | Custom limit respected | | Yes — `TestValidatePluginsOutputLimitsUsesTotalPayloadOverride` |
| **P1** | Model ↔ API Run round-trip | 1. `model.Run` → API Run → verify plugin fields | Preserved | | Yes — `TestToModelRunPluginsFields`, `TestToApiRunPluginsFields` |

#### 4.1.10 Storage Layer

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | Create run with plugin fields | 1. Create `model.Run` with `PluginsInputString` + `PluginsOutputString`<br>2. Read back | Both fields persisted | | Yes — `run_store_test.go::TestCreateRunWithPluginsFields` |
| **P0** | Create run without plugin fields → NULL | 1. Create run without plugin fields<br>2. Verify DB columns NULL | Fields nil in returned model | | Yes — `run_store_test.go::TestCreateRunWithEmptyPluginsFieldsWritesNull` |
| **P0** | `UpdateRunPluginsOutput` only updates output column | 1. Create run<br>2. Call `UpdateRunPluginsOutput`<br>3. Verify other fields unchanged | Only `PluginsOutput` column updated | | Yes — `run_store_test.go::TestUpdateRunPluginsOutputOnly` |
| **P0** | `UpdateRunPluginsOutput` for nonexistent run | 1. Call with unknown UUID | Returns not-found error | | Yes — `run_store_test.go::TestUpdateRunPluginsOutputNotFound` |
| **P1** | Update run preserves plugin fields | 1. Create run with plugin fields<br>2. Update run conditions/state<br>3. Verify plugin fields unchanged | Plugin fields not overwritten | | Yes — `run_store_test.go::TestUpdateRunPreservesPluginsFields` |
| **P1** | Create job with `PluginsInput` | 1. Create `model.Job` with `PluginsInputString`<br>2. Read back | `PluginsInputString` persisted | | Yes — `job_store_test.go::TestCreateJobPluginsInput` |

#### 4.1.11 Workflow Utility

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | `SetEnvVarsToDriverAndLauncherTemplates` injects env vars | 1. Workflow with templates containing Container + InitContainers<br>2. Call with env vars<br>3. Verify all containers | Env vars on all main containers and init containers | | Partial — tested via resource_manager integration |
| **P0** | `SetMLflowEnabledFlag` adds `--mlflow_enabled` | 1. Templates with `--type` (driver) and `--copy` (launcher) args<br>2. Call `SetMLflowEnabledFlag`<br>3. Verify args | `--mlflow_enabled` appended only to matching containers | | Partial — logic exists, needs dedicated unit test |
| **P1** | `appendEnvNoDuplicates` skips existing vars | 1. Existing env has `FOO=bar`<br>2. Try to add `FOO=baz` | `FOO=bar` kept; no duplicate | | Partial — indirectly tested |
| **P1** | `hasArg` helper | 1. Test with matching and non-matching flags | Returns true/false correctly | | No — simple helper |
| **P2** | Empty env vars map → no-op | 1. Call `SetEnvVarsToDriverAndLauncherTemplates({})` | No changes to templates | | Yes — `config.go::InjectMLflowRuntimeEnv` nil-check |

#### 4.1.12 Plugin Limits Configuration

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | Default limits applied | 1. No limits configured<br>2. Call `GetPluginLimitsConfig()` | Defaults: MaxKeys=16, MaxPayloadBytes=64KB, MaxTotalPayloadBytes=256KB, MaxNestingDepth=10 | | Yes — `config_test.go::TestGetPluginLimitsConfigDefaults` |
| **P1** | Custom limits via config | 1. Set custom values<br>2. Call `GetPluginLimitsConfig()` | Custom values returned | | Yes — `config_test.go::TestGetPluginLimitsConfigOverrides` |
| **P1** | Invalid limit values rejected | 1. Set non-integer or negative values<br>2. Call `GetPluginLimitsConfig()` | Error returned | | Yes — `TestGetPluginLimitsConfigRejectsInvalidValues` |
| **P2** | Overflow values rejected | 1. Set extremely large int values | Error returned | | Yes — `TestGetPluginLimitsConfigRejectsOverflow` |
| **P2** | Cross-field invariant validation | 1. Set `MaxPayloadBytes > MaxTotalPayloadBytes` | Error returned | | Yes — `TestGetPluginLimitsConfigRejectsCrossFieldInvariant` |

#### 4.1.13 AutoMigrate / DB Schema

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | AutoMigrate adds new columns | 1. Run `autoMigrate` with `AllModels()`<br>2. Verify `PluginsInput` and `PluginsOutput` columns exist on `run_details`<br>3. Verify `PluginsInput` column on `jobs` | Nullable TEXT columns created | | Yes — `client_manager_test.go::TestAutoMigrateSucceeds` |
| **P1** | Existing data unaffected by migration | 1. Pre-existing rows without plugin columns<br>2. Run migration<br>3. Query existing rows | NULL values for new columns; existing data intact | | Partial — GORM behavior, implicitly tested |

---

### 4.2 Negative Functional Tests

#### 4.2.1 Invalid Input Handling

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | Malformed `plugins_input` JSON | 1. Call `ResolveMLflowPluginInput` with `{bad` | Error: "plugins_input must be a valid JSON object" | | Yes — `config_test.go::TestResolveMLflowPluginInput` |
| **P0** | Unknown field in `plugins_input.mlflow` | 1. Provide `{"mlflow": {"experiment_name": "a", "unknown": "b"}}`<br>2. Validate | Error rejecting unknown field (DisallowUnknownFields) | | Yes — `config_test.go::TestResolveMLflowPluginInput` |
| **P0** | `plugins_input.mlflow` must be object | 1. Provide `{"mlflow": "string"}`<br>2. Validate | Error: "must follow schema..." | | Yes — `config_test.go::TestResolveMLflowPluginInput` |
| **P1** | Payload exceeding `MaxTotalPayloadBytes` | 1. Large `plugins_input`<br>2. Validate | Limit violation error | | Yes — `api_converter_test.go::TestValidatePluginsInputLimits` |
| **P1** | Exceeding nesting depth | 1. Deeply nested JSON<br>2. Validate | Nesting depth error | | Yes — `api_converter_test.go` |
| **P1** | Exceeding `MaxKeys` | 1. Many top-level plugin keys<br>2. Validate | Key count error | | Yes — `api_converter_test.go` |

#### 4.2.2 MLflow Failure Handling (Graceful Degradation)

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | MLflow unreachable on CreateRun | 1. Configure unreachable MLflow endpoint<br>2. Call `CreateRun` | KFP run still created; `plugins_output.mlflow.state` = `PLUGIN_FAILED` with error message | | Yes — `handler_test.go::TestOnRunStart_MLflowFailure_ReturnsFailedOutput` |
| **P0** | MLflow 5xx on experiment lookup | 1. Mock 500 response<br>2. Call `OnRunStart` | Run created; `state_message` contains error | | Yes — `handler_test.go::TestOnRunStart_MLflowFailure_ReturnsFailedOutput` |
| **P1** | Config unavailable on terminal sync | 1. Remove global config<br>2. Report terminal state on run with MLflow output | `plugins_output.mlflow.state` = `PLUGIN_FAILED`: "config unavailable" | | Yes — `handler_test.go::TestOnRunEnd_NilConfig_SetsFailedState` |
| **P1** | Config unavailable on retry | 1. Remove global config<br>2. Call RetryRun | `plugins_output.mlflow.state` = `PLUGIN_FAILED`: "config unavailable" | | Yes — `handler_test.go::TestHandleRetry_NilConfig_SetsFailedState` |
| **P1** | MLflow failure on terminal sync | 1. Mock unreachable MLflow<br>2. Report terminal state | `state` = `PLUGIN_FAILED` with sync error message | | Partial — handler tests missing-root-ID case |

#### 4.2.3 Configuration Errors

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | Missing `credentialSecretRef` for bearer auth | 1. `authType: "bearer"` without `credentialSecretRef`<br>2. Resolve | Error: "credentialSecretRef.name is required" | | Yes — `config_test.go::TestBuildMLflowRequestContextMissingSecretRefValidation` |
| **P0** | Missing Secret for credential resolution | 1. Reference nonexistent Secret<br>2. Resolve | Error: "credential secret not found" | | Yes — implicit in k8sfake behavior |
| **P1** | Invalid endpoint URL | 1. `endpoint: "not-a-url"` | Error: "invalid plugins.mlflow endpoint" | | Yes — `config.go` validation |
| **P1** | Invalid timeout | 1. `timeout: "not-a-duration"` | Error: "invalid plugins.mlflow timeout" | | Yes — `config.go` validation |
| **P1** | Zero timeout | 1. `timeout: "0s"` | Error: "timeout must be > 0" | | Yes — `config.go` validation |
| **P1** | Unsupported auth type | 1. `authType: "oauth2"` | Error: "unsupported plugins.mlflow.settings.authType" | | Yes — `config.go` switch default |
| **P1** | Empty token for kubernetes auth | 1. SA token file exists but is empty<br>2. Resolve | Error: "token is empty" | | Yes — `config.go` validation |
| **P1** | Empty password for basic-auth | 1. Secret exists, password key is empty<br>2. Resolve | Error: "must be non-empty" | | Yes — `config.go` validation |

#### 4.2.4 Edge Cases

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | `OnRunStart` with nil handler | 1. Call on nil `Handler` | Returns `nil, nil` (no-op) | | Yes — `handler.go` nil check |
| **P0** | `OnRunStart` with nil run | 1. `OnRunStart(ctx, nil, config)` | Returns `nil, nil` | | Yes — `handler.go` nil check |
| **P0** | `OnRunStart` with disabled plugin | 1. `plugins_input.mlflow.disabled: true`<br>2. Call `OnRunStart` | Returns `nil, nil` | | Yes — `handler_test.go::TestOnRunStart_Disabled_ReturnsNil` |
| **P0** | `OnRunStart` with nil input | 1. Construct handler with `nil` input<br>2. Call `OnRunStart` | Returns `nil, nil` | | Yes — `handler_test.go::TestOnRunStart_NilInput_ReturnsNil` |
| **P0** | `OnRunStart` with nil config | 1. Call `OnRunStart(ctx, run, nil)` | Returns `nil, nil` | | Yes — `handler_test.go::TestOnRunStart_NilConfig_ReturnsNil` |
| **P0** | `OnRunEnd` with nil run | 1. `OnRunEnd(ctx, nil, config)` | Returns nil (no-op) | | Yes — `handler_test.go::TestOnRunEnd_NilRun_ReturnsNil` |
| **P1** | `OnRunEnd` with no `plugins_output` | 1. Run has no `plugins_output` map<br>2. Call `OnRunEnd` | Returns nil (no-op) | | Yes — `handler_test.go::TestOnRunEnd_NoPluginOutput_ReturnsNil` |
| **P1** | `OnRunEnd` with missing `root_run_id` | 1. `plugins_output.mlflow` exists but no `root_run_id` entry<br>2. Call `OnRunEnd` | `state` = `PLUGIN_FAILED`: "missing parent root_run_id" | | Yes — `handler_test.go::TestOnRunEnd_MissingRootRunID_SetsFailedState` |
| **P1** | `HandleRetry` with no `plugins_output` | 1. Run without plugin output<br>2. Call `HandleRetry` | No-op | | Yes — `handler_test.go::TestHandleRetry_NoPluginOutput_NoOp` |
| **P1** | `HandleRetry` with missing `root_run_id` | 1. `plugins_output.mlflow` exists but no `root_run_id`<br>2. Call `HandleRetry` | `state` = `PLUGIN_FAILED` | | Yes — `handler_test.go::TestHandleRetry_MissingRootRunID_SetsFailedState` |
| **P2** | `SyncPluginOutputToModel` merges with existing entries | 1. Model has existing plugin entries<br>2. API run has new entries<br>3. Sync | Existing entries preserved, new entries added/overwritten | | Yes — `handler_test.go::TestSyncPluginOutputToModel_MergesWithExisting` |
| **P2** | `ModelToPluginRun` with nil model | 1. Call with nil | Returns nil | | Yes — `handler_test.go::TestModelToPluginRun_NilModel` |

---

### 4.3 Security Tests

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | SA token not in Argo Workflow spec | 1. `authType: "kubernetes"`<br>2. Inspect workflow templates after env injection | No raw token values in templates; only `KFP_MLFLOW_CONFIG` JSON (which does not contain the token) | | Manual / Integration |
| **P0** | Secret values not in workflow spec | 1. `authType: "bearer"` with Secret<br>2. Inspect workflow templates | Secret values not embedded in templates | | Manual / Integration |
| **P1** | Bearer token read from correct Secret key | 1. Custom `tokenKey` in `credentialSecretRef`<br>2. Resolve | Token from specified key | | Yes — `config_test.go::TestBuildMLflowRequestContextSecretBasedAuth` |
| **P1** | Empty token rejected | 1. Secret key exists but empty<br>2. Resolve | Error: "must be non-empty" | | Yes — `config.go` validation |
| **P2** | HTTPS endpoint uses TLS | 1. `endpoint: "https://mlflow.example.com"`<br>2. Verify client config | TLS config applied to HTTP client | | Yes — `config.go::BuildHTTPClient` |
| **P2** | Custom CA bundle loaded | 1. `tls.caBundlePath` to valid PEM<br>2. Build client | Custom CA pool used | | Yes — `config.go::BuildHTTPClient` |
| **P2** | Invalid CA bundle path | 1. `tls.caBundlePath` to nonexistent file | Error: "failed to read caBundlePath" | | Yes — error path in `BuildHTTPClient` |

---

### 4.4 Boundary Tests

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P1** | Max `plugins_input` payload size | 1. Exactly at limit → accepted<br>2. One byte over → rejected | Correct enforcement | | Yes — `api_converter_test.go` |
| **P1** | Max `plugins_output` payload size | 1. Same for output | Correct enforcement | | Yes — `api_converter_test.go` |
| **P1** | Max nesting depth | 1. Deeply nested JSON | Depth error | | Yes — `api_converter_test.go` |
| **P1** | Max plugin key count | 1. Many top-level keys | Key count error | | Yes — `api_converter_test.go` |
| **P2** | Timeout boundary for MLflow | 1. `timeout: "1ms"` → slow server | Timeout; graceful degradation | | Partial — `BuildHTTPClient` sets timeout |
| **P2** | Max search pages cap (100) | 1. MLflow returns `next_page_token` indefinitely | Loop exits after 100 pages | | Yes — `run_start.go::maxSearchPages` constant |
| **P2** | Empty `experiment_name` defaults to "Default" | 1. Empty or missing `experiment_name`<br>2. Verify | Defaults to "Default" | | Yes — `config_test.go::TestResolveMLflowPluginInput` |

---

### 4.5 Performance Tests

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P2** | CreateRun latency with MLflow | 1. Enable MLflow<br>2. Measure latency vs baseline | < 2s additional (within configured timeout) | | No — manual benchmark |
| **P2** | Terminal sync with many nested runs | 1. 100+ nested runs<br>2. Report terminal state<br>3. Measure sync | Completes within 60s (retry elapsed); no OOM | | No — manual benchmark |
| **P3** | Concurrent CreateRun with MLflow | 1. 50 concurrent requests<br>2. All succeed | No race conditions; no duplicate experiments | | No — manual load test |
| **P3** | DB impact of LargeText columns | 1. 10,000 runs with plugin fields<br>2. ListRuns performance | No significant degradation | | No — manual benchmark |

---

### 4.6 Cluster Configuration Tests

#### 4.6.1 Standalone Mode

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | Standalone with global MLflow config | 1. Deploy KFP standalone + MLflow<br>2. Set `plugins.mlflow` in config<br>3. Create run → complete → retry | Full lifecycle works; MLflow experiment/run created, tagged, synced | | No — cluster integration |
| **P1** | Standalone without MLflow config | 1. Deploy KFP standalone, no `plugins.mlflow`<br>2. Create run | No MLflow activity; backward compatible | | No — regression (existing E2E) |

#### 4.6.2 Multi-Tenant Cluster

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P1** | Namespace-level MLflow config | 1. Deploy multi-user KFP<br>2. Set `kfp-launcher` ConfigMap with `plugins.mlflow` in namespace<br>3. Create run | Namespace config used; workspace = namespace | | No — cluster integration |
| **P1** | Namespace overrides global endpoint | 1. Global endpoint A, namespace endpoint B<br>2. Create run in namespace | MLflow calls go to B | | No — cluster integration |
| **P2** | Namespace without config inherits global | 1. Global config present, no namespace ConfigMap<br>2. Create run in namespace | Global config used | | No — cluster integration |

#### 4.6.3 FIPS Mode

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P2** | MLflow TLS in FIPS mode | 1. FIPS-enabled cluster<br>2. HTTPS MLflow endpoint<br>3. Create run | TLS uses FIPS-compliant ciphers | | No — FIPS cluster |
| **P3** | Custom CA in FIPS mode | 1. `tls.caBundlePath` with FIPS-compliant CA | Connection works | | No — FIPS cluster |

#### 4.6.4 Disconnected Cluster

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P2** | MLflow on internal network | 1. Air-gapped cluster<br>2. Internal MLflow endpoint<br>3. Create run | MLflow integration works; no external calls | | No — disconnected cluster |
| **P3** | MLflow unreachable in disconnected | 1. No MLflow deployed<br>2. Config points to nonexistent endpoint<br>3. Create run | Run created; `PLUGIN_FAILED` with timeout message | | No — disconnected cluster |

---

### 4.7 Final Regression / Full E2E Tests

| Priority | Test Case Summary | Test Steps | Expected Result | Actual Result | Automated? |
|---|---|---|---|---|---|
| **P0** | E2E: Create → complete → verify MLflow | 1. Deploy KFP + MLflow on Kind<br>2. Create run with `plugins_input`<br>3. Wait for completion<br>4. Verify MLflow experiment, parent run, tags<br>5. Verify `plugins_output` via GetRun | Full lifecycle end-to-end | | No — cluster integration; automatable in Ginkgo |
| **P0** | E2E: Create without MLflow config | 1. Deploy KFP without MLflow<br>2. Create pipeline run | Run succeeds normally; no regressions | | Yes — existing E2E suite |
| **P0** | E2E: Retry failed run → MLflow reopened | 1. Deploy KFP + MLflow<br>2. Create failing run<br>3. Wait for failure<br>4. Retry<br>5. Verify MLflow parent/nested reopened | Parent and FAILED/KILLED nested runs set to RUNNING | | No — cluster integration |
| **P0** | E2E: Recurring run triggers with MLflow | 1. Create recurring run with `plugins_input`<br>2. Wait for triggered run<br>3. Verify triggered run has MLflow parent | Each triggered run gets own MLflow parent run | | No — cluster integration |
| **P1** | E2E: Delete run → MLflow orphan | 1. Create and complete a run<br>2. Delete KFP run<br>3. Check MLflow | MLflow run remains (orphan acceptable per design) | | No — cluster integration |
| **P1** | Regression: Existing E2E pass without MLflow | 1. Run `ginkgo -v ./backend/test/end2end`<br>2. All pass | No regressions | | Yes — CI (`e2e-test.yml`) |
| **P1** | Regression: API integration tests pass | 1. Run `ginkgo -v ./backend/test/v2/api`<br>2. All pass | Existing API tests pass | | Yes — CI (`api-server-tests.yml`) |
| **P1** | Regression: Compiler tests pass | 1. Run `ginkgo -v ./backend/test/compiler`<br>2. All goldens match | No regressions | | Yes — CI (`compiler-tests.yml`) |
| **P1** | Regression: Go unit tests pass | 1. Run `go test -v $(go list ./backend/... \| grep -v backend/test/)`<br>2. All pass | All new + existing tests pass | | Yes — CI |

---

## 5. Test Gaps & Recommendations

| # | Gap | Severity | Recommendation |
|---|---|---|---|
| 1 | No dedicated unit tests for `SetEnvVarsToDriverAndLauncherTemplates` and `SetMLflowEnabledFlag` on `workflow.go` | Medium | Add unit tests with mock Argo Workflow objects to verify correct template targeting, no-duplicate logic, and `--mlflow_enabled` flag placement |
| 2 | No explicit test for namespace-only enablement (global absent, namespace present) | Medium | Add unit test to verify `ResolveMLflowRequestConfig` returns config when `hasGlobal=false, hasNamespace=true` |
| 3 | No explicit retry/backoff test for `common/mlflow/client.go` | Medium | Add unit test mocking transient 5xx → 200 to verify exponential backoff and permanent error on 4xx |
| 4 | `plugins_output` accepted on CreateRun API request (not rejected/ignored) | Low | Verify `api_converter.go::toModelRun` ignores user-provided `plugins_output`; current code has comment but no enforcement |
| 5 | No E2E test automation for MLflow integration in CI | High | Add Ginkgo test suite under `backend/test/v2/api/` with `MLflow` label; requires MLflow deployment in CI Kind cluster |
| 6 | No test for `CloneRun` plugin propagation | Low | Out of scope; track as follow-up |
| 7 | No test for `secretKeyRef` credential injection on templates | Medium | Out of scope; track for driver/launcher follow-up |
| 8 | `MLflowRuntimeConfig` JSON field names alignment test | Medium | Add test that marshals `MLflowRuntimeConfig` and verifies JSON keys match KEP (`endpoint`, `parentRunId`, `experimentId`, `authType`, `timeout`, `insecureSkipVerify`) |
| 9 | No multi-user cluster E2E test | Medium | Add CI job deploying multi-user KFP + MLflow; test namespace-scoped config |
| 10 | No `CreateRun` resource_manager integration test (only Retry has one) | Medium | Add `TestCreateRun_WithMLflowPlugin` integration test in `resource_manager_test.go` |

---

## 6. CI/CD Integration

### 6.1 Existing CI Coverage

| Workflow | What It Tests | MLflow Coverage |
|---|---|---|
| `api-server-tests.yml` | Ginkgo API integration tests | No MLflow tests yet; must not regress |
| `e2e-test.yml` | End-to-end pipeline execution | No MLflow tests; backward compatibility |
| `compiler-tests.yml` | Compiled workflow goldens | Must pass; env injection doesn't affect goldens |
| `ci-checks.yml` | Go build, vet, lint | New files must compile and pass lint |
| `frontend.yml` | Frontend tests | Not affected |

### 6.2 Recommended New CI Jobs

| Job Name | Description | Trigger |
|---|---|---|
| `mlflow-integration-tests` | Deploy KFP + MLflow on Kind; run Ginkgo tests labeled `MLflow` | PRs touching `backend/src/apiserver/mlflow/**`, `backend/src/common/mlflow/**` |
| `mlflow-recurring-run-tests` | Deploy KFP + MLflow; create recurring runs; verify triggered runs | Same as above |

---

## 7. Test Data Requirements

| Item | Details |
|---|---|
| Mock MLflow server | `httptest.NewServer` with handlers for all 6 REST endpoints |
| Pipeline YAML files | Existing test pipelines under `test_data/pipeline_files/valid/` |
| Kubernetes Secrets | Fake secrets via `k8sfake.NewSimpleClientset` for auth tests |
| ConfigMaps | Fake `kfp-launcher` ConfigMap for namespace-level config tests |
| SA token file | Temp file via `os.CreateTemp` for kubernetes auth tests |
| MLflow deployment | Docker image `ghcr.io/mlflow/mlflow:latest` for cluster integration |
| Proto golden files | `backend/test/proto_tests/testdata/generated-1791485/` |

---

## 8. Sign-off Criteria

- [ ] All P0 and P1 unit tests pass (`go test -v ./backend/src/apiserver/...`)
- [ ] All existing CI checks pass (no regressions)
- [ ] P0 E2E tests pass on a local Kind cluster with MLflow deployed
- [ ] Code coverage for new files ≥ 80%
- [ ] No security issues identified (no secrets in workflow specs)
- [ ] Plugin field validation prevents oversized payloads
- [ ] Graceful degradation verified: KFP runs succeed when MLflow is down
- [ ] Proto golden files updated and passing
- [ ] AutoMigrate adds new columns without data loss
