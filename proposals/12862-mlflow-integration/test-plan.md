# KEP-12862: MLflow Integration — Test Plan

**Feature**: Pipeline Run Lifecycle Hooks for MLflow Integration  
**Branch**: `pipeline-run-api-hooks`  
**Design Doc**: [KEP-12862 README](./README.md)  
**Last Updated**: 2026-03-18  

---

## 1. Scope & Objectives

This test plan covers all changes introduced by the `pipeline-run-api-hooks` branch, which adds:

1. **Proto changes** — `plugins_input` / `plugins_output` fields on `Run` (fields 19, 20) and `RecurringRun` (field 19), plus `PluginOutput`, `MetadataValue`, `PluginState`.
2. **MLflow handler** — `OnRunStart`, `OnRunEnd`, `HandleRetry` lifecycle hooks (`backend/src/apiserver/mlflow/handler.go`).
3. **Config resolution** — Global (Viper) + namespace (ConfigMap) merge, auth credential resolution (`backend/src/apiserver/mlflow/config.go`).
4. **MLflow helpers** — Experiment creation, run tagging, nested run sync, plugin output serialization (`backend/src/apiserver/mlflow/run_start.go`).
5. **Shared MLflow HTTP client** — `GetExperimentByName`, `CreateExperiment`, `CreateRun`, `UpdateRun`, `SetTag`, `SearchRuns` with retry (`backend/src/common/mlflow/client.go`).
6. **Shared types** — `PluginConfig`, `MLflowRuntimeConfig`, `MLflowCredentials`, etc. (`backend/src/common/mlflow/config.go`).
7. **Task handler stubs** — `TaskPluginHandler`, `TaskInfo`, `TaskStartResult` for future driver/launcher work (`backend/src/common/mlflow/handler.go`).
8. **Env var injection** — `KFP_MLFLOW_CONFIG` JSON env var + `--mlflow_enabled` flag on Argo templates (`backend/src/common/util/workflow.go`).
9. **Resource manager integration** — `applyMLflowOnRunStart` (before workflow create), `applyMLflowOnRunEnd`, `applyMLflowOnRunRetry` (`backend/src/apiserver/resource/resource_manager.go`).
10. **Recurring run propagation** — `PluginsInput` on `ScheduledWorkflowSpec`; SWF controller passes it to each triggered run.
11. **Data layer** — Serialization, validation, storage, model↔API conversion for plugin fields.
12. **Plugin limits** — Configurable `MaxKeys`, `MaxPayloadBytes`, `MaxTotalPayloadBytes`, `MaxNestingDepth`.
13. **AutoMigrate** — Centralized `AllModels()` adds new nullable columns.

### Out of Scope (for this PR)

- Driver / Launcher MLflow integration (`OnTaskStart`, `OnTaskEnd` stubs only).
- SDK changes (`plugins_input` parameter on client methods).
- Frontend rendering of `plugins_output`.
- `CloneRun` plugin propagation.
- `secretKeyRef` credential mounting on Argo templates.

---

## 2. Changed Files

| # | File | Change Summary |
|---|---|---|
| 1 | `backend/api/v2beta1/run.proto` | Added `plugins_input` (19), `plugins_output` (20), `PluginOutput`, `MetadataValue`, `PluginState` |
| 2 | `backend/api/v2beta1/recurring_run.proto` | Added `plugins_input` (19) |
| 3–8 | `backend/api/v2beta1/{go_client,go_http_client,python_http_client,swagger}/...` | Generated code |
| 9 | `backend/src/apiserver/mlflow/config.go` | Config resolution, auth, env var injection |
| 10 | `backend/src/apiserver/mlflow/config_test.go` | 12 unit tests |
| 11 | `backend/src/apiserver/mlflow/handler.go` | `PluginHandler`, `Handler`, `OnRunStart`, `OnRunEnd`, `HandleRetry` |
| 12 | `backend/src/apiserver/mlflow/handler_test.go` | 19 tests (+ table-driven) |
| 13 | `backend/src/apiserver/mlflow/run_start.go` | MLflow experiment/run helpers, plugin output serialization |
| 14 | `backend/src/common/mlflow/client.go` | Shared REST client (6 methods + retry) |
| 15 | `backend/src/common/mlflow/config.go` | Shared types/constants/utilities |
| 16 | `backend/src/common/mlflow/handler.go` | `TaskPluginHandler` stubs |
| 17 | `backend/src/common/util/workflow.go` | `SetEnvVarsToDriverAndLauncherTemplates`, `SetMLflowEnabledFlag` |
| 18 | `backend/src/apiserver/resource/resource_manager.go` | `applyMLflowOnRunStart/End/Retry`, `applyMLflowPostAction` |
| 19 | `backend/src/apiserver/resource/resource_manager_test.go` | 2 integration tests |
| 20 | `backend/src/apiserver/server/api_converter.go` | Plugin serialization, validation |
| 21 | `backend/src/apiserver/server/api_converter_test.go` | 15 tests |
| 22–23 | `backend/src/apiserver/storage/{run_store,job_store}.go` | `UpdateRunPluginsOutput`, plugin persistence |
| 24–25 | `backend/src/apiserver/storage/{run_store,job_store}_test.go` | 7 tests |
| 26–27 | `backend/src/apiserver/storage/{sql_null_util,db_fake}.go` | Helpers + fake DB |
| 28–29 | `backend/src/apiserver/model/{run,job}.go` | `PluginsInput/OutputString` fields |
| 30 | `backend/src/apiserver/model/common.go` | `AllModels()` |
| 31–32 | `backend/src/apiserver/common/{const,config}.go` | Plugin limits defaults + `GetPluginLimitsConfig` |
| 33 | `backend/src/apiserver/common/config_test.go` | 6 tests |
| 34 | `backend/src/apiserver/main.go` | Plugin limits validation at startup |
| 35 | `backend/src/apiserver/template/v2_template.go` | `PluginsInput` propagation to SWF |
| 36–37 | `backend/src/apiserver/client_manager/client_manager{,_test}.go` | `AllModels()` migration |
| 38–39 | `backend/src/crd/controller/scheduledworkflow/{controller,controller_test}.go` | `parsePluginsInputJSON`, propagation |
| 40 | `backend/src/crd/pkg/apis/scheduledworkflow/v1beta1/types.go` | `PluginsInput` on `ScheduledWorkflowSpec` |
| 41 | `backend/test/proto_tests/testdata/generated-1791485/...` | Updated golden files |

---

## 3. Existing Test Coverage

| Test File | Tests | Focus |
|---|---|---|
| `mlflow/config_test.go` | 12 | Config, merging, auth (kubernetes/bearer/basic-auth), experiment ops, terminal status |
| `mlflow/handler_test.go` | 19 | OnRunStart/OnRunEnd/HandleRetry (success, nil, failure), URL building, plugin output sync, nested run pagination |
| `server/api_converter_test.go` | 15 | JSON↔proto serialization, validation limits, model↔API round-trip |
| `storage/run_store_test.go` | 6 | CRUD with plugin fields, NULL handling, UpdateRunPluginsOutput |
| `storage/job_store_test.go` | 1 | Job CRUD with PluginsInput |
| `resource/resource_manager_test.go` | 2 | CreateRun + RetryRun MLflow integration |
| `crd/controller_test.go` | 5 | `parsePluginsInputJSON` valid/invalid cases |
| `common/config_test.go` | 6 | Plugin limits defaults/overrides/invalid |
| `client_manager_test.go` | 1 | AutoMigrate with AllModels() |

**Total: ~67 new tests**

---

## 4. Test Plan

### 4.1 CreateRun with MLflow (Happy Path)

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | Default experiment name | 1. Configure global `plugins.mlflow`<br>2. CreateRun without `plugins_input` | Experiment "Default" created; parent run created; `plugins_output.mlflow` has `experiment_id`, `root_run_id`, `run_url`; state = `PLUGIN_SUCCEEDED` | Yes — `handler_test.go::TestOnRunStart_Success` |
| **P0** | Custom experiment name | 1. CreateRun with `plugins_input.mlflow.experiment_name = "my-exp"` | Experiment "my-exp" created; parent run under it | Partial — handler covers; cluster needed |
| **P0** | `experiment_id` precedence | 1. Provide both `experiment_name` and `experiment_id` | `experiment_id` used; no name lookup | Yes — `config_test.go::TestSelectMLflowExperiment` |
| **P0** | `KFP_MLFLOW_CONFIG` injected | 1. OnRunStart succeeds<br>2. Check workflow templates | JSON env var with `endpoint`, `parentRunId`, `experimentId`, `authType`, `timeout`, `insecureSkipVerify` on all driver/launcher containers | Yes — `handler_test.go`, `resource_manager_test.go` |
| **P0** | `--mlflow_enabled` flag | 1. OnRunStart → MLflowEnabled=true<br>2. Check template args | Flag appended to `--type` (driver) and `--copy` (launcher) containers only | Yes — `workflow.go` logic |
| **P0** | Injection before workflow create | 1. Verify `applyMLflowOnRunStart` before `workflowClient.Create` | Env vars baked in before Kubernetes submission | Yes — `resource_manager.go` ordering |
| **P1** | KFP metadata tags | 1. Create run with `pipeline_id`, `pipeline_version_id` | Tags: `kfp.pipeline_run_id`, `kfp.pipeline_run_url`, `kfp.pipeline_id`, `kfp.pipeline_version_id` | Yes — `config_test.go::TestCreateParentRunAndTagWithKFPMetadata` |
| **P1** | URL formats | 1. `BuildKFPRunURL(id)` → `/#/runs/details/<id>`<br>2. `BuildRunURL(ctx)` → `<endpoint>/experiments/<id>/runs/<id>?workspace=<ns>` | Correct URL patterns | Yes — `handler_test.go::TestBuildKFPRunURL` |
| **P1** | Experiment description defaults | 1. No desc → "Created by Kubeflow Pipelines"<br>2. Empty string → no desc<br>3. Custom → custom | All three handled | Yes — `run_start.go::ResolveExperimentDescription` |
| **P2** | Race-safe experiment creation | 1. Two concurrent calls; second gets `RESOURCE_ALREADY_EXISTS` | Falls back to `GetExperimentByName`; both succeed | Yes — `run_start.go::CreateExperiment` logic |

### 4.2 Terminal State (OnRunEnd)

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | SUCCEEDED → FINISHED | 1. Report terminal SUCCEEDED | Parent run marked FINISHED; `state = PLUGIN_SUCCEEDED` | Yes — `handler_test.go::TestOnRunEnd_Success` |
| **P0** | FAILED → FAILED | 1. Report terminal FAILED | Parent run marked FAILED | Yes — `config_test.go::TestToMLflowTerminalStatus` |
| **P0** | CANCELED → KILLED | 1. Report terminal CANCELED | Parent run marked KILLED | Yes — `config_test.go::TestToMLflowTerminalStatus` |
| **P1** | Active nested runs closed | 1. Parent has RUNNING/SCHEDULED nested runs<br>2. Report terminal | All active nested runs synced via paginated `SearchRuns` + `UpdateRun` | Yes — `handler_test.go::TestSyncParentAndNestedRuns_Pagination` |
| **P1** | Output persisted after sync | 1. OnRunEnd updates state<br>2. SyncPluginOutputToModel<br>3. UpdateRunPluginsOutput | State persisted to DB | Yes — `resource_manager.go` + `run_store_test.go::TestUpdateRunPluginsOutputOnly` |

### 4.3 RetryRun

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | Reopens parent + failed/killed nested | 1. Failed run with MLflow output<br>2. RetryRun | Parent → RUNNING; FAILED/KILLED nested → RUNNING; FINISHED left alone | Yes — `handler_test.go::TestHandleRetry_Success`, `resource_manager_test.go` |
| **P1** | No `plugins_output` → no-op | 1. Failed run without MLflow<br>2. RetryRun | No MLflow calls; no errors | Yes — `handler_test.go::TestHandleRetry_NoPluginOutput_NoOp` |

### 4.4 Recurring Runs

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | Job stores `plugins_input` | 1. CreateJob with `plugins_input`<br>2. Read back | `PluginsInputString` persisted | Yes — `job_store_test.go`, `api_converter_test.go` |
| **P0** | SWF → triggered run propagation | 1. Job → SWF spec → controller parses → CreateRun | Each triggered run inherits `plugins_input` | Yes — `controller_test.go::TestParsePluginsInputJSON`, `v2_template.go` |

### 4.5 Data Layer (Serialization, Storage, Round-Trip)

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | `plugins_input` JSON ↔ proto round-trip | 1. Serialize map → JSON → deserialize back | Structure and values preserved | Yes — `api_converter_test.go::TestPluginsInputToJSON`, `TestJSONToPluginsInput` |
| **P0** | `plugins_output` JSON ↔ proto round-trip | 1. Same for output with entries, state, state_message | Preserved incl. `render_type: URL` | Yes — `api_converter_test.go::TestPluginsOutputToJSON`, `TestJSONToPluginsOutput` |
| **P0** | Create run with plugin fields → read back | 1. Create `model.Run` with both fields<br>2. Read from store<br>3. Convert to API | End-to-end preservation | Yes — `run_store_test.go::TestCreateRunWithPluginsFields`, `api_converter_test.go::TestToApiRunPluginsFields` |
| **P0** | NULL plugin fields | 1. Create run without plugins<br>2. Read back | Fields nil; no errors | Yes — `run_store_test.go::TestCreateRunWithEmptyPluginsFieldsWritesNull` |
| **P0** | `UpdateRunPluginsOutput` (success + not-found) | 1. Update existing → success<br>2. Update nonexistent → error | Only output column updated; not-found error | Yes — `run_store_test.go::TestUpdateRunPluginsOutputOnly`, `TestUpdateRunPluginsOutputNotFound` |
| **P1** | Update run preserves plugin fields | 1. Create with plugins<br>2. Update conditions/state | Plugin fields unchanged | Yes — `run_store_test.go::TestUpdateRunPreservesPluginsFields` |
| **P1** | ListRuns returns plugin fields | 1. Create multiple runs<br>2. ListRuns | All include plugin fields | Yes — `run_store_test.go::TestListRunsReturnsPluginsFields` |
| **P1** | Proto golden file validation | 1. Run proto tests against `generated-1791485/` goldens | `plugins_input: {}` / `plugins_output: {}` in goldens | Yes — proto test suite |
| **P0** | AutoMigrate adds new columns | 1. Run `autoMigrate(AllModels())`<br>2. Verify new nullable columns | `PluginsInput`/`PluginsOutput` on `run_details`; `PluginsInput` on `jobs` | Yes — `client_manager_test.go::TestAutoMigrateSucceeds` |

### 4.6 Payload Validation & Limits

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | Default limits applied | 1. No config<br>2. `GetPluginLimitsConfig()` | MaxKeys=16, MaxPayload=64KB, MaxTotal=256KB, MaxDepth=10 | Yes — `config_test.go::TestGetPluginLimitsConfigDefaults` |
| **P0** | Payload exceeds `MaxTotalPayloadBytes` | 1. Large `plugins_input` or `plugins_output`<br>2. Validate | Limit violation error | Yes — `api_converter_test.go::TestValidatePluginsInputLimits`, `TestValidatePluginsOutputLimits` |
| **P1** | Custom limits respected | 1. Override limits via config<br>2. Validate | Custom values enforced | Yes — `TestValidatePluginsInputLimitsUsesConfiguredOverrides`, `TestGetPluginLimitsConfigOverrides` |
| **P1** | Nesting depth exceeded | 1. Deeply nested JSON | Depth error | Yes — `TestValidatePluginsInputLimitsUsesNestingDepthOverride` |
| **P1** | Key count exceeded | 1. Many top-level plugin keys | Key count error | Yes — `api_converter_test.go` |
| **P1** | Invalid limit config rejected | 1. Non-integer, negative, overflow values | Error from `GetPluginLimitsConfig` | Yes — `TestGetPluginLimitsConfigRejectsInvalidValues`, `TestGetPluginLimitsConfigRejectsOverflow` |
| **P2** | `MaxPayloadBytes > MaxTotalPayloadBytes` | 1. Cross-field violation | Error | Yes — `TestGetPluginLimitsConfigRejectsCrossFieldInvariant` |
| **P2** | Max search pages cap (100) | 1. Infinite `next_page_token` | Loop exits after 100 pages | Yes — `run_start.go::maxSearchPages` |

### 4.7 MLflow Configuration & Auth

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | Global config resolution | 1. Set `plugins.mlflow` in Viper<br>2. `GetGlobalMLflowConfig()` | Valid `PluginConfig` returned | Yes — `config_test.go::TestGetGlobalMLflowConfig` |
| **P0** | `kubernetes` auth → SA token | 1. `authType: "kubernetes"`<br>2. `ResolveMLflowCredentials` | Bearer token from `ServiceAccountTokenPath`; no secrets leaked into templates | Yes — `config_test.go::TestBuildMLflowRequestContextKubernetesAuth` |
| **P0** | `bearer` auth → Secret | 1. `authType: "bearer"` with `credentialSecretRef`<br>2. Resolve | Token from referenced Secret key | Yes — `config_test.go::TestBuildMLflowRequestContextSecretBasedAuth` |
| **P0** | `basic-auth` → Secret | 1. `authType: "basic-auth"` with `credentialSecretRef`<br>2. Resolve | Username + password from Secret | Yes — `config_test.go::TestBuildMLflowRequestContextSecretBasedAuth` |
| **P0** | Missing `credentialSecretRef` for bearer | 1. `authType: "bearer"` without ref | Error: "credentialSecretRef.name is required" | Yes — `config_test.go::TestBuildMLflowRequestContextMissingSecretRefValidation` |
| **P1** | Namespace merges with global | 1. Global endpoint A; namespace endpoint B | Endpoint = B; timeout inherited | Yes — `config_test.go::TestMergePluginConfigAndSettingsDefaults` |
| **P1** | Namespace-only enablement | 1. No global config<br>2. Namespace ConfigMap has `plugins.mlflow` | Config from namespace only | Partial — logic implemented, needs explicit test |
| **P1** | Namespace override requires credentials | 1. Namespace overrides endpoint, no `credentialSecretRef` | Error | Yes — validation in `config.go` |
| **P1** | Unsupported auth type | 1. `authType: "oauth2"` | Error: "unsupported" | Yes — `config.go` switch default |
| **P1** | Empty token / empty password | 1. SA token empty or Secret key empty | Error: "must be non-empty" | Yes — `config.go` validation |
| **P1** | Invalid endpoint / timeout / zero timeout | 1. Malformed values | Appropriate errors | Yes — `config.go` validation |
| **P1** | `X-MLflow-Workspace` header | 1. Enable workspaces<br>2. Any API call | Header present | Yes — `config_test.go` |
| **P2** | `WorkspacesEnabled` auth-type defaults | 1. kubernetes → true; bearer → false | Correct defaults | Yes — `config_test.go` |
| **P2** | TLS: custom CA bundle / invalid path | 1. Valid PEM → custom CA pool<br>2. Bad path → error | Correct behavior | Yes — `BuildHTTPClient` |

### 4.8 Negative & Edge Cases

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | MLflow unreachable on CreateRun | 1. Unreachable endpoint<br>2. CreateRun | KFP run created; `state = PLUGIN_FAILED` with message | Yes — `handler_test.go::TestOnRunStart_MLflowFailure_ReturnsFailedOutput` |
| **P0** | Nil handler / nil run / nil config → no-op | 1. Call OnRunStart with nil | Returns `nil, nil` | Yes — `handler_test.go::TestOnRunStart_Nil*` |
| **P0** | Disabled plugin → no-op | 1. `plugins_input.mlflow.disabled: true` | Returns `nil, nil` | Yes — `handler_test.go::TestOnRunStart_Disabled_ReturnsNil` |
| **P0** | Malformed `plugins_input` JSON | 1. `ResolveMLflowPluginInput` with `{bad` | Error | Yes — `config_test.go::TestResolveMLflowPluginInput` |
| **P0** | Unknown field in `plugins_input.mlflow` | 1. `{"mlflow": {"unknown": "b"}}` | Error (DisallowUnknownFields) | Yes — `config_test.go` |
| **P1** | Config unavailable on OnRunEnd/HandleRetry | 1. Nil config<br>2. Call hook | `state = PLUGIN_FAILED`: "config unavailable" | Yes — `handler_test.go::TestOnRunEnd_NilConfig`, `TestHandleRetry_NilConfig` |
| **P1** | Missing `root_run_id` on OnRunEnd/HandleRetry | 1. `plugins_output.mlflow` exists but no `root_run_id` | `state = PLUGIN_FAILED` | Yes — `handler_test.go::TestOnRunEnd_MissingRootRunID`, `TestHandleRetry_MissingRootRunID` |
| **P1** | OnRunEnd with no `plugins_output` | 1. Run without plugin output | No-op | Yes — `handler_test.go::TestOnRunEnd_NoPluginOutput` |
| **P1** | 4xx errors → permanent (no retry) | 1. Mock 400 | `backoff.Permanent` error | Yes — `client.go::doWithRetry` |
| **P1** | 5xx errors → retry | 1. Mock 500 then 200 | Retried; succeeds | Partial — logic present, explicit test needed |
| **P2** | `SyncPluginOutputToModel` merges entries | 1. Existing + new entries | Merged correctly | Yes — `handler_test.go::TestSyncPluginOutputToModel_MergesWithExisting` |
| **P2** | `ModelToPluginRun` with nil | 1. Nil model | Returns nil | Yes — `handler_test.go` |

### 4.9 Workflow Template Injection

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | Env vars on all driver/launcher containers | 1. Workflow with Container + InitContainers<br>2. `SetEnvVarsToDriverAndLauncherTemplates` | Env vars on main + init containers | Partial — via resource_manager |
| **P0** | `--mlflow_enabled` only on matching containers | 1. `SetMLflowEnabledFlag`<br>2. Check `--type`/`--copy` containers | Flag appended only to driver/launcher | Partial — needs dedicated unit test |
| **P1** | No duplicate env vars | 1. Existing `FOO=bar`<br>2. Try to add `FOO=baz` | Original kept; no duplicate | Partial — indirectly tested |
| **P2** | Empty env map → no-op | 1. `SetEnvVarsToDriverAndLauncherTemplates({})` | Templates unchanged | Yes — nil-check in `InjectMLflowRuntimeEnv` |

---

### 4.10 Performance Tests

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P2** | CreateRun latency with MLflow | 1. Measure with vs without MLflow | < 2s additional | No — manual |
| **P2** | Terminal sync with 100+ nested runs | 1. Report terminal<br>2. Measure | Completes within 60s; no OOM | No — manual |
| **P3** | Concurrent CreateRun (50 requests) | 1. Blast requests | No races; no duplicate experiments | No — manual |

---

### 4.11 Cluster & E2E Tests

| Pri | Test Case | Steps | Expected | Automated? |
|---|---|---|---|---|
| **P0** | Full lifecycle (standalone) | 1. KFP + MLflow on Kind<br>2. CreateRun with `plugins_input` → complete → GetRun | MLflow experiment/run created, tagged, synced; `plugins_output` populated | No — cluster |
| **P0** | Retry failed run | 1. Create failing run → fail → RetryRun<br>2. Check MLflow | Parent + FAILED nested reopened | No — cluster |
| **P0** | Recurring run triggers with MLflow | 1. Create recurring with `plugins_input`<br>2. Wait for triggered run | Triggered run gets own MLflow parent | No — cluster |
| **P0** | No MLflow config → backward compatible | 1. Deploy KFP without `plugins.mlflow`<br>2. Create run | Runs succeed normally; no regressions | Yes — existing E2E |
| **P1** | Multi-user: namespace-level config | 1. Set `kfp-launcher` ConfigMap with `plugins.mlflow` in namespace | Namespace config used; workspace = namespace | No — cluster |
| **P1** | Delete run → MLflow orphan | 1. Complete run<br>2. Delete KFP run<br>3. Check MLflow | MLflow run remains (by design) | No — cluster |
| **P1** | Regression: E2E + API + compiler tests pass | 1. Run existing Ginkgo suites | No regressions | Yes — CI |
| **P2** | FIPS mode: MLflow TLS | 1. FIPS cluster + HTTPS MLflow | FIPS-compliant ciphers | No — FIPS cluster |
| **P2** | Disconnected: internal MLflow | 1. Air-gapped + internal endpoint | Works; no external calls | No — disconnected cluster |
| **P3** | Disconnected: MLflow unreachable | 1. Config points to nonexistent endpoint | `PLUGIN_FAILED` with timeout | No — disconnected cluster |

---

## 5. Test Gaps & Recommendations

| # | Gap | Severity | Recommendation |
|---|---|---|---|
| 1 | No dedicated unit tests for `SetEnvVarsToDriverAndLauncherTemplates` / `SetMLflowEnabledFlag` | Medium | Add unit tests with mock Argo Workflow objects |
| 2 | No explicit test for namespace-only enablement (global absent) | Medium | Add unit test for `ResolveMLflowRequestConfig` with namespace-only config |
| 3 | No explicit retry/backoff test for `client.go` | Medium | Add test mocking 5xx → 200 |
| 4 | `plugins_output` accepted on CreateRun request (not rejected) | Low | Verify `toModelRun` ignores user-provided `plugins_output` |
| 5 | No E2E test automation for MLflow in CI | High | Add Ginkgo suite with `MLflow` label; deploy MLflow in CI Kind cluster |
| 6 | `MLflowRuntimeConfig` JSON field alignment test | Medium | Marshal and verify keys match KEP |
| 7 | No `CreateRun` resource_manager integration test (only Retry exists) | Medium | Add `TestCreateRun_WithMLflowPlugin` |

---

## 6. CI/CD Integration

### Existing Coverage

| Workflow | MLflow Coverage |
|---|---|
| `api-server-tests.yml` | No MLflow; must not regress |
| `e2e-test.yml` | No MLflow; backward compatibility |
| `compiler-tests.yml` | Must pass; env injection doesn't affect goldens |
| `ci-checks.yml` | New files must compile + lint |

### Recommended New Jobs

| Job | Description | Trigger |
|---|---|---|
| `mlflow-integration-tests` | KFP + MLflow on Kind; Ginkgo `MLflow` label | PRs touching `apiserver/mlflow/**`, `common/mlflow/**` |

---

## 7. Test Data Requirements

| Item | Details |
|---|---|
| Mock MLflow server | `httptest.NewServer` with 6 REST endpoints |
| Pipeline YAMLs | `test_data/pipeline_files/valid/` |
| K8s Secrets / ConfigMaps | `k8sfake.NewSimpleClientset` |
| SA token file | `os.CreateTemp` |
| MLflow deployment | `ghcr.io/mlflow/mlflow:latest` for cluster integration |
| Proto goldens | `backend/test/proto_tests/testdata/generated-1791485/` |

---

## 8. Sign-off Criteria

- [ ] All P0 and P1 unit tests pass (`go test -v ./backend/src/apiserver/...`)
- [ ] All existing CI checks pass (no regressions)
- [ ] P0 E2E tests pass on local Kind cluster with MLflow
- [ ] Code coverage for new files ≥ 80%
- [ ] No secrets leaked into workflow specs
- [ ] Oversized payloads rejected
- [ ] Graceful degradation: KFP runs succeed when MLflow is down
- [ ] Proto golden files updated and passing
- [ ] AutoMigrate adds columns without data loss
