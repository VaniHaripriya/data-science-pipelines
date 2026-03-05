# Database Migration for MLMD Removal

**Status**: Design Review
**Author**: @vmudadla
**Created**: 2026-02-26

## Summary

This proposal describes the database migration strategy for migrating historical pipeline metadata from ML Metadata (MLMD) to native KFP tables as part of the MLMD removal effort.

## Motivation

When upgrading KFP to a version without MLMD, existing MLMD data (executions, artifacts, events) must be migrated to the new native KFP database schema. This migration must be safe, idempotent, and support both manual and automatic execution modes.

## Design Details

See [database-migration-design.md](../database-migration-design.md) for complete design.

### Key Features

1. **Idempotent Migration** - Can run multiple times, migrates only delta
2. **Dual Execution Modes**:
   - Standalone CLI tool for manual control
   - API server integration for automatic migration
3. **Shared Code** - 95% code reuse between both modes
4. **Zero Downtime** - API server serves traffic during migration
5. **Resumable** - Checkpoint-based recovery from interruptions

### File Changes

```
backend/src/apiserver/
├── migration/                          # NEW: Shared migration engine
│   ├── manager.go                      # Migration orchestration
│   ├── transformers.go                 # MLMD → KFP transformations
│   ├── checkpoint.go                   # Idempotency & resume
│   └── validation.go                   # Validation logic
│
├── model/
│   ├── migration_status.go             # NEW: Migration tracking
│   └── mlmd_id_map.go                  # NEW: ID mapping
│
└── main.go                             # MODIFIED: Migration check

backend/cmd/mlmd-migrate/               # NEW: CLI tool
└── main.go                             # CLI tool entry point
```

## Usage

### Manual Migration (Standalone CLI)
```bash
mlmd-migrate \
  --mlmd-address=metadata-grpc-service:8080 \
  --mysql-host=mysql:3306 \
  --batch-size=5000
```

### Automatic Migration (API Server)
```yaml
env:
  - name: MLMD_MIGRATE
    value: "true"
```

## Testing

- Unit tests for transformers and idempotency
- Integration tests with test MLMD database
- Load tests with 1M+ entities
- Multi-replica coordination tests

## Implementation

Implementation will be done in a follow-up PR after design approval.
