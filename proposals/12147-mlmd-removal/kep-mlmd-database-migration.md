# KEP: MLMD to KFP Native Database Migration

## Table of Contents

1. [Summary](#summary)
2. [Motivation](#motivation)
3. [Goals](#goals)
4. [Non-Goals](#non-goals)
5. [Proposal](#proposal)
   - [User Stories](#user-stories)
   - [Design Details](#design-details)
6. [Alternatives Considered](#alternatives-considered)
7. [Risks and Mitigations](#risks-and-mitigations)
8. [Test Plan](#test-plan)
9. [Graduation Criteria](#graduation-criteria)
10. [Implementation Plan](#implementation-plan)
11. [Open Questions](#open-questions)
12. [References](#references)

---

## Summary

This KEP proposes a database migration subsystem to transfer historical pipeline metadata — executions, artifacts, and events — from ML Metadata (MLMD) into KFP's native MySQL-backed schema. This migration is a prerequisite for the broader MLMD removal effort ([#12147](https://github.com/kubeflow/pipelines/issues/12147)). Without it, operators upgrading from a MLMD-backed KFP version to a future MLMD-free version would permanently lose their run history, task records, and artifact lineage.

---

## Motivation

KFP has historically used MLMD to record pipeline execution metadata. MLMD introduces operational overhead — an additional gRPC service, a separate MySQL schema, and a complex deployment dependency — for data that KFP could store natively in its own MySQL tables.

The MLMD removal initiative (tracked in #12147) eliminates this dependency from the KFP backend. However, removing MLMD without a migration path would silently discard all historical run data for every existing KFP deployment. Operators rely on this data for compliance, audit, reproducibility, and debugging. Silent data loss is not acceptable.

This KEP describes a migration engine that:

- Preserves historical runs, tasks, artifacts, and artifact-task linkages by copying them from MLMD into KFP's native `tasks`, `artifacts`, and `artifact_tasks` tables.
- Allows upgrades to proceed without a maintenance window.
- Is safe to run multiple times without creating duplicates or corrupting live data.

---

## Goals

1. **Data preservation** — All executions, artifacts, and events recorded in MLMD are migrated into the KFP native schema accurately and completely, preserving important fields and lineage relationships.
2. **Zero-downtime** — The API server continues to serve traffic during data migration.
3. **Idempotency** — The migration can be run multiple times. Repeated runs produce no duplicates and leave the database in a consistent state.
4. **Resumability** — A migration interrupted by a pod crash, SIGTERM, or node failure can resume from a checkpoint without replaying previously migrated entities.
5. **Multi-replica safety** — In HA deployments where multiple API server replicas are running, exactly one replica performs the migration at a time.
6. **Dual execution modes** — Operators can run migration automatically on API server startup or manually via a standalone CLI tool.

---

## Proposal

### User Stories

**Story 1: Operator upgrading an existing KFP deployment**

> As a KFP platform operator, I want to upgrade from a MLMD-backed version of KFP to a MLMD-free version without losing any historical pipeline run data or artifact lineage, so that my team can continue to audit and debug past runs after the upgrade.

**Story 2: Operator with limited maintenance window**

> As a KFP operator at a large organization, I cannot take the API server offline for more than a few minutes. I want the migration to run in the background while the API server is live so that my users experience no downtime during the upgrade.

**Story 3: Operator preferring manual control**

> As a KFP operator who manages migration windows carefully, I want to run the migration as a standalone job on my own schedule — before or after the API server upgrade — so I can control when the extra database load occurs and verify results before proceeding.

**Story 4: Recovery from a failed migration**

> As a KFP operator, if the migration fails partway through (e.g., due to a pod restart), I want to be able to re-trigger it and have it resume where it left off, rather than restarting from scratch.

---

### Design Details

#### Architecture

The migration system has three components that share a single migration engine:

```
┌─────────────────────────────────────────────────────────────┐
│                    Migration Engine                          │
│            backend/src/apiserver/migration/                 │
│  manager.go · transformers.go · checkpoint.go · validation.go│
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
┌─────────▼──────────┐       ┌──────────▼───────────┐
│  Standalone CLI     │       │  API Server           │
│  backend/cmd/       │       │  backend/src/apiserver│
│  mlmd-migrate/      │       │  main.go              │
│  main.go            │       │  (background goroutine│
│  (manual, blocking) │       │   after schema migr.) │
└────────────────────┘       └──────────────────────┘
```

Both execution modes use identical migration logic. Only the entry point and configuration source differ.

#### File Structure

```
backend/src/apiserver/
├── migration/                        # NEW: Shared migration engine
│   ├── manager.go                    # Migration orchestration & state machine
│   ├── transformers.go               # MLMD entity → KFP model transformations
│   ├── checkpoint.go                 # Idempotency tracking & resume logic
│   ├── validation.go                 # Pre/post migration validation
│   └── models.go                     # Migration tracking DB models
│
├── model/
│   ├── migration_status.go           # NEW: Migration status tracking
│   ├── migration_checkpoint.go       # NEW: Resume checkpoint tracking
│   └── mlmd_id_map.go                # NEW: MLMD ID → KFP UUID mapping
│
└── main.go                           # MODIFIED: Migration check on startup

backend/cmd/
└── mlmd-migrate/                     # NEW: Standalone CLI tool
    └── main.go                       # CLI wrapper around migration engine
```

#### Migration Phases

**Phase 1 — Pre-migration validation** (~seconds, synchronous)

- Verify MLMD gRPC connectivity.
- Verify MySQL connectivity and sufficient disk space.
- Confirm all MLMD contexts (runs) have a corresponding row in `run_details`. Orphaned MLMD records (contexts without a `run_details` counterpart) are logged as warnings and skipped rather than failing the entire migration. This handles common partial-failure states from past runs.

**Phase 2 — Schema migration** (~5–10s, synchronous, blocks API server startup)

- GORM `AutoMigrate` creates or reconciles the `tasks`, `artifacts`, `artifact_tasks`, `migration_status`, and `mlmd_id_map` tables.
- Blocks API server startup intentionally: the server must not write to these tables before they exist.

**Phase 3 — Data migration** (background, non-blocking)

Entities are migrated in dependency order to satisfy foreign key constraints:

```
MLMD Executions  ──►  tasks table
                       (deterministic UUID, state mapping, TaskType detection)

MLMD Artifacts   ──►  artifacts table
                       (metrics split into separate rows, register in mlmd_id_map)

MLMD Events      ──►  artifact_tasks table       ← LAST: FK deps on both above
                       (link tasks to artifacts, preserve IOType)

Second pass      ──►  Resolve parent_task_uuid references via mlmd_id_map
```

The background goroutine (API Server mode) starts immediately after Phase 2 completes. Historical data becomes visible in the UI progressively as records are committed. New runs written by the live API server are unaffected.

**Phase 4 — Post-migration validation**

- Entity count comparison (MLMD executions ≈ KFP tasks; MLMD events = KFP artifact_tasks).
- TaskType distribution sanity check (presence of ROOT, RUNTIME, etc.).
- Foreign key integrity spot-check.
- Cache fingerprint verification (only `SUCCEEDED`/`CACHED` tasks should have a fingerprint).

#### New Database Tables

**`migration_status`** — tracks overall migration state across restarts:

```sql
CREATE TABLE migration_status (
    ID               INT AUTO_INCREMENT PRIMARY KEY,
    MigrationName    VARCHAR(128) NOT NULL UNIQUE,
    Status           VARCHAR(32)  NOT NULL,  -- NOT_STARTED|IN_PROGRESS|COMPLETED|FAILED
    StartedAt        BIGINT,
    CompletedAt      BIGINT,
    LastCheckpoint   TEXT,                   -- JSON checkpoint (last processed IDs)
    ErrorMessage     TEXT,
    TotalEntities    BIGINT DEFAULT 0,
    MigratedEntities BIGINT DEFAULT 0,
    CurrentStage     VARCHAR(64)
);
```

**`mlmd_id_map`** — maps MLMD integer IDs to KFP UUIDs for parent-task resolution and rollback:

```sql
CREATE TABLE mlmd_id_map (
    mlmd_entity_type VARCHAR(20)  NOT NULL,   -- "execution" or "artifact"
    mlmd_id          BIGINT       NOT NULL,
    kfp_uuid         VARCHAR(191) NOT NULL,
    migrated_at      BIGINT       NOT NULL,
    PRIMARY KEY (mlmd_entity_type, mlmd_id)
);
```

`mlmd_id_map` is a temporary table and may be dropped 30–90 days after migration completes.

#### Idempotency

Three overlapping mechanisms ensure the migration is safe to run multiple times:

**1. Deterministic UUID generation (UUID v5)**

MLMD integer IDs are mapped to UUIDs deterministically using UUID v5 (SHA-1 based):

```
Input:  MLMD Execution ID = 12345
Step 1: Namespace string = "execution:12345"
Step 2: SHA-1 hash with DNS namespace
Step 3: Format as UUID v5 = "a1b2c3d4-e5f6-5789-abcd-ef0123456789"
```

The same MLMD ID always produces the same UUID. Live API server writes use random UUID v4; these two namespaces never collide.

**2. Safe insert semantics**

```sql
INSERT IGNORE INTO tasks (UUID, ...) VALUES (...);
```

Duplicate rows (same UUID) are silently skipped. A crashed-and-resumed run encounters `RowsAffected = 0` for already-migrated rows and `RowsAffected = 1` for new ones — no errors, no duplicates.

**3. Checkpoint-based resume**

Progress is persisted in `migration_status.LastCheckpoint` as a JSON cursor:

```json
{
  "last_execution_id": 1000,
  "last_artifact_id": 5000,
  "last_migration_timestamp": 1709000000
}
```

On resume, MLMD is queried with `WHERE id > last_execution_id ORDER BY id ASC`, skipping already-processed batches. Even if the checkpoint is lost, deterministic UUIDs + `INSERT IGNORE` guarantee correctness — checkpoints are a performance optimization, not a correctness requirement.

#### MLMD Entity Transformations

**Executions → Tasks (TaskType detection)**

| MLMD Execution Type | Detection Logic | KFP TaskType |
|---|---|---|
| `system.DAGExecution` (no parent) | No `parent_dag_id` | ROOT (0) |
| `system.ContainerExecution` | Type check | RUNTIME (1) |
| `system.DAGExecution` (condition-branches-*) | Name prefix | CONDITION_BRANCH (2) |
| `system.DAGExecution` (condition-*) | Name prefix, child of CONDITION_BRANCH | CONDITION (3) |
| `system.DAGExecution` + `iteration_count` | Custom property | LOOP (4) |
| `system.DAGExecution` (exit-handler-*) | Name prefix; fallbacks: on-exit-*, onexit-*, or custom prop | EXIT_HANDLER (5) |
| `system.ImporterExecution` | Type check | IMPORTER (6) |
| `system.DAGExecution` (with parent) | Has `parent_dag_id` | DAG (7) |

Detection order is significant: specific patterns (exit-handler, condition, loop) are evaluated before falling back to generic DAG.

**MLMD State → KFP TaskState**

| MLMD State | KFP TaskState | Notes |
|---|---|---|
| `NEW` | RUNTIME_STATE_UNSPECIFIED (0) | |
| `RUNNING` | RUNNING (1) | |
| `COMPLETE` | SUCCEEDED (2) | |
| `FAILED` | FAILED (4) | |
| `CACHED` | CACHED (5) | |
| `CANCELED` | FAILED (4) | No CANCELED in KFP TaskState; maps to FAILED |

Cache fingerprints are copied only for `COMPLETE` or `CACHED` executions to prevent incomplete executions from poisoning the cache.

**Artifacts → Artifacts (metrics splitting)**

MLMD stores scalar metrics as a single artifact with multiple key-value custom properties. KFP stores each metric as a separate row with a `NumberValue` field. A single MLMD metrics artifact with N metrics produces N KFP artifact rows. Only the first metric's UUID is registered in `mlmd_id_map` — it is the UUID that `artifact_tasks` uses when linking events back to the original MLMD artifact. (See Open Questions #1.)

#### Multi-Replica Safety

MySQL advisory locks prevent concurrent migration in HA deployments:

```sql
SELECT GET_LOCK('kfp_mlmd_migration_lock', 10);
-- Returns 1: lock acquired, proceed with migration
-- Returns 0: another replica holds lock, skip and continue serving
```

Locks are session-scoped and auto-release on connection loss or crash — no manual cleanup required.

#### Execution Modes

**Mode 1 — Standalone CLI (manual)**

```bash
mlmd-migrate \
  --mlmd-address=metadata-grpc-service:8080 \
  --mysql-host=mysql:3306 \
  --batch-size=5000 \
  --workers=8
```

- Runs in foreground, blocks until complete.
- Exits 0 on success, non-zero on failure.
- Supports `--resume` flag to restart from last checkpoint.
- Configuration via CLI flags.

**Mode 2 — API Server integration (automatic)**

```yaml
env:
  - name: MLMD_MIGRATE
    value: "true"
  - name: RETRY_FAILED_MIGRATION
    value: "false"
  - name: MIGRATION_BATCH_SIZE
    value: "1000"
  - name: MIGRATION_WORKERS
    value: "2"
```

- Schema migration (Phase 2) runs synchronously at startup.
- Data migration (Phase 3) runs in a background goroutine; the API server begins serving traffic immediately after Phase 2.
- If `Status=COMPLETED`, migration is skipped entirely on subsequent restarts.
- If `Status=FAILED` and `RETRY_FAILED_MIGRATION=true`, migration retries from the last checkpoint.

#### Rollback

MLMD is kept running for 30–90 days after migration completes to allow rollback:

```sql
-- 1. Remove all migrated artifact linkages and artifacts (new tables: safe to truncate)
DELETE FROM artifact_tasks;
DELETE FROM artifacts;

-- 2. Remove only migrated tasks (tasks is a pre-existing table; preserve non-MLMD rows)
DELETE FROM tasks WHERE UUID IN (
  SELECT kfp_uuid FROM mlmd_id_map WHERE mlmd_entity_type = 'execution'
);
```

After deletion: revert to the previous API server image and restart with MLMD enabled.

#### Error Handling

| Error Type | Behavior |
|---|---|
| Individual entity transformation failure | Log warning, skip entity, continue |
| Missing optional MLMD properties | Log warning, use default, continue |
| MLMD gRPC connection loss | Fatal: set `Status=FAILED`, surface error |
| MySQL connection loss | Fatal: set `Status=FAILED`, surface error |
| Disk space exhaustion | Fatal: set `Status=FAILED`, surface error |
| Schema mismatch | Fatal: set `Status=FAILED`, surface error |

Recovery: set `RETRY_FAILED_MIGRATION=true` and restart, or re-run the CLI with `--resume`.

---

## Alternatives Considered

### Alternative 1: Blocking migration at API server startup

Run the full migration synchronously during startup, holding all traffic until complete.

**Rejected because:** For deployments with large MLMD databases (millions of executions), migration could take tens of minutes to hours. A maintenance window of that duration is unacceptable for production systems.

### Alternative 2: CLI tool only, no automatic API server integration

Require operators to always run migration manually before upgrading.

**Rejected because:** This adds a mandatory manual step that many operators will miss. An automatic opt-in path (`MLMD_MIGRATE=true`) significantly reduces upgrade friction while still supporting manual control.

### Alternative 3: Read-through layer proxying historical queries to MLMD

Instead of migrating data, proxy historical queries to MLMD while new data is written natively.

**Rejected because:** This perpetuates the MLMD dependency indefinitely and significantly complicates the query layer. The goal of #12147 is to eliminate MLMD entirely.

### Alternative 4: Use MLMD integer IDs directly as KFP record identifiers

Avoid UUID generation by reusing MLMD integer IDs.

**Rejected because:** KFP's schema and API surface use UUID strings throughout. Changing this would break existing clients and downstream integrations. Deterministic UUID v5 preserves the UUID contract while achieving idempotency.

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Migration load degrades database performance | Medium | Configurable `--batch-size` and `--workers`; operators can tune or schedule the CLI tool during off-peak hours |
| Pod crash during migration loses checkpoint | Low | Deterministic UUIDs + `INSERT IGNORE` guarantee safety even without a checkpoint; checkpoint is a performance optimization only |
| Orphaned MLMD contexts (no matching `run_details` row) | Low | Phase 1 validation detects these; they are skipped with a warning rather than failing the migration |
| `mlmd_id_map` corruption prevents rollback | Low | Document UUID v5 recomputation as a fallback rollback path that does not depend on `mlmd_id_map` |
| Post-migration artifact count higher than expected due to metrics splitting | Low | Post-migration validation checks artifact count is within a configurable ratio bound (not just ≥ MLMD count) |
| Silently skipped entities not detected | Medium | Post-migration entity count comparison surfaces significant discrepancies as validation failures |

---

## Test Plan

### Unit Tests

- Entity transformation functions for all TaskType detection paths, including edge cases (missing custom properties, unknown execution types, exit-handler fallback chain).
- State mapping for all MLMD → KFP TaskState transitions including `CANCELED`.
- Deterministic UUID v5 generation: same input always produces same UUID; execution and artifact namespaces never collide; no collision with UUID v4 space.
- Metrics artifact splitting: N key-value pairs produce exactly N KFP artifact rows; only first UUID registered in `mlmd_id_map`.
- Checkpoint serialization and deserialization.
- `INSERT IGNORE` idempotency: running the same entity through the engine twice produces exactly one row.
- Cache fingerprint gating: fingerprint present only for `COMPLETE`/`CACHED` states.

### Integration Tests

- **Full migration:** Seed a test MLMD database with executions, artifacts, and events across all TaskTypes. Run migration. Assert KFP tables contain expected records with correct state, UUID, type, and relationships.
- **Delta migration:** Run migration on initial dataset. Add new MLMD records. Re-run. Assert only new records are added; existing records are unchanged.
- **Resume after crash:** Inject a failure mid-way through Phase 3. Restart migration. Assert the final state is identical to a clean run.
- **Checkpoint loss:** Run migration, delete `LastCheckpoint`, restart. Assert idempotency: no duplicate rows, no errors.
- **Large metrics artifacts:** Seed MLMD with multi-metric artifacts. Assert correct splitting and `mlmd_id_map` registration.
- **Orphaned MLMD contexts:** Include MLMD contexts without matching `run_details` rows. Assert they are skipped with a warning and remaining data is migrated correctly.

### Multi-Replica Tests

- Start two API server replicas simultaneously with `MLMD_MIGRATE=true`. Assert exactly one replica acquires the lock and runs the migration. Assert the other replica logs a skip message and continues serving traffic. Assert final data state is correct and contains no duplicates.

### Rollback Tests

- Run full migration. Execute rollback SQL. Assert `tasks` contains only pre-migration rows; `artifacts` and `artifact_tasks` are empty. Restart API server with MLMD enabled and confirm prior behavior.

---

## Graduation Criteria

This KEP is **Provisional**. The following criteria must be met before it moves to **Implementable**:

- [ ] Resolution of open questions below (particularly metrics split `mlmd_id_map` semantics and checkpoint cursor ordering guarantee).
- [ ] Review and approval from at least one KFP backend approver.
- [ ] Alignment with the parent MLMD removal proposal (#12147) on sequencing and target release.

This KEP moves to **Complete** when:

- [ ] All implementation tasks in the Implementation Plan are merged.
- [ ] Unit and integration tests pass in CI.
- [ ] The migration is exercised in at least one upgrade integration test.
- [ ] Operator documentation is updated with upgrade instructions covering both execution modes, rollback procedure, and `mlmd_id_map` retention guidance.

---

## Implementation Plan

1. **Migration engine** — Implement `backend/src/apiserver/migration/`: `manager.go`, `transformers.go`, `checkpoint.go`, `validation.go`, `models.go`.
2. **Standalone CLI** — Implement `backend/cmd/mlmd-migrate/main.go` as a thin wrapper over the engine.
3. **API Server integration** — Modify `backend/src/apiserver/main.go` to check env vars, run Phase 2 synchronously, and spawn Phase 3 as a background goroutine.
4. **Schema** — Add `migration_status` and `mlmd_id_map` table definitions; implement `migration_status.go`, `migration_checkpoint.go`, `mlmd_id_map.go` GORM models.
5. **Unit tests** — Cover all transformation paths, UUID generation, and idempotency.
6. **Integration tests** — Full migration, delta migration, resume-after-crash, multi-replica coordination, rollback.
7. **Documentation** — Operator upgrade guide covering both execution modes, rollback procedure, and `mlmd_id_map` retention window.

---

## Open Questions

1. **Metrics split and `mlmd_id_map` registration** — When a single MLMD metrics artifact is split into N KFP artifact rows, only the first metric's UUID is registered in `mlmd_id_map`. This means `artifact_tasks` can only reference one of the N generated rows. Is this the intended semantic? If an MLMD event referenced a metrics artifact, should `artifact_tasks` link to all N split rows, or only the first?

2. **MLMD gRPC ordering guarantee** — The checkpoint cursor (`last_execution_id`) assumes MLMD returns executions in ascending ID order. Does the MLMD gRPC API guarantee stable ascending-ID ordering? If not, the cursor strategy may miss records on resume and needs revision.

3. **Worker concurrency and checkpoint cursor** — The `--workers` flag implies parallel batch processing. If workers process non-contiguous ID ranges concurrently, a simple `last_execution_id` cursor may not accurately represent resume progress. Should the checkpoint store a set of completed batch ranges instead?

4. **Phase 1 failure behavior for orphaned contexts** — The current design warns and skips MLMD contexts that have no matching `run_details` row. Should the migration instead fail-fast and report a count of orphaned records, giving operators the opportunity to investigate before proceeding?

5. **`migration_status` checkpoint storage** — `LastCheckpoint` is currently a JSON `TEXT` column in `migration_status`. A dedicated `migration_checkpoint.go` model is already planned. Should the checkpoint be normalized into its own table row rather than embedded JSON, for consistency with the rest of the schema design?

---

## References

- [Main MLMD Removal Proposal – README.md](../12147-mlmd-removal/README.md)
- [Design Details](../12147-mlmd-removal/design-details.md)
- [Schema Changes SQL](../12147-mlmd-removal/schema_changes.sql)
- [Test Plan](../12147-mlmd-removal/test_plan.md)
- [KFP CONTRIBUTING.md – KEP Process](https://github.com/kubeflow/pipelines/blob/master/CONTRIBUTING.md)
- [ML Metadata (google/ml-metadata)](https://github.com/google/ml-metadata)
