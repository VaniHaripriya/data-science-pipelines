# Database Migration Proposal - PR Guide

## Overview

This is a **design-only PR** following the pattern from [proposal 11385-literal-input-parameters](https://github.com/kubeflow/pipelines/tree/master/proposals/11385-literal-input-parameters).

**Key Principle:** Design first, implementation later.

## What's in This PR

### ✅ Design Documents Only

```
proposals/12147-mlmd-removal/
├── README.md                           # Existing - main MLMD removal proposal
├── design-details.md                   # Existing - upstream design
├── test_plan.md                        # Existing - test strategy
├── schema_changes.sql                  # Existing - DB schema
├── database-migration-design.md        # 🆕 Complete migration design
└── database-migration/                 # 🆕 This proposal subdirectory
    ├── README.md                       # 🆕 Quick summary
    ├── COMMIT_CHECKLIST.md            # 🆕 Commit guide (this file)
    └── PR_GUIDE.md                    # 🆕 PR guide (optional)
```

### ❌ No Implementation Code

Following the 11385 pattern, **no Go code** is included:
- No `backend/src/apiserver/migration/*.go`
- No `backend/cmd/mlmd-migrate/*.go`
- No `backend/src/apiserver/model/migration_*.go`

Implementation will come in a **follow-up PR** after design approval.

## What the Design Covers

### 1. Architecture (`database-migration-design.md`)

**Dual Execution Modes:**
- Standalone CLI tool (manual control)
- API server integration (automatic)
- **95% shared code** between both modes

**Key Design Decision:** Both use same migration engine, only entry point differs.

### 2. Migration Strategy

**Idempotency:**
- Deterministic UUID generation (same MLMD ID → same UUID)
- INSERT IGNORE pattern (skip duplicates)
- Checkpoint-based resume

**Data Flow:**
```
MLMD Executions → KFP tasks table
MLMD Artifacts  → KFP artifacts table (metrics split into separate rows)
MLMD Events     → KFP artifact_tasks table
```

### 3. Key Transformations

**Exit Handler Detection:**
- Primary: Name prefix `exit-handler-*`
- Matches requirement from main proposal

**Cache Fingerprints:**
- Only set for COMPLETE or CACHED executions
- Matches requirement from main proposal

**Metrics Storage:**
- Stored in artifacts table with Type=Metric
- Each metric gets separate row with NumberValue
- Different from original requirement (separate Metrics table), but simpler

### 4. File Structure

Shows where implementation will go:
```
backend/src/apiserver/
├── migration/          # NEW - shared migration engine
│   ├── manager.go
│   ├── transformers.go
│   ├── checkpoint.go
│   └── validation.go
│
├── model/
│   └── migration_status.go  # NEW
│
└── main.go            # MODIFIED

backend/cmd/mlmd-migrate/
└── main.go            # NEW - CLI wrapper
```

## How to Commit This PR

### 1. Review Files

```bash
cd /home/vmudadla/workspace/data-science-pipelines
cd proposals/12147-mlmd-removal
ls -la
```

Should see:
- ✅ database-migration-design.md (new design doc)
- ✅ database-migration/ (new subdirectory)
- ✅ README.md, design-details.md, test_plan.md (existing, don't touch)
- ✅ schema_changes.sql (existing, reference only)

### 2. Stage Files

```bash
# Stage new files only
git add proposals/12147-mlmd-removal/database-migration-design.md
git add proposals/12147-mlmd-removal/database-migration/

# Verify what you're committing
git status
```

### 3. Create Commit

```bash
git commit -m "feat(backend): Database migration design for MLMD removal

- Design document for migrating MLMD data to native KFP tables
- Supports both CLI tool and API server integration modes
- Idempotent migration with checkpoint-based resume
- Follows design pattern from proposal 11385

This is a design-only PR. Implementation will follow in separate PR.

Signed-off-by: Your Name <your.email@example.com>
"
```

### 4. Create PR

**Title:**
```
feat(backend): Database migration design for MLMD removal
```

**Description:**
```markdown
## Summary
Design document for migrating historical MLMD data to native KFP database tables.

## Motivation
As part of the MLMD removal effort (see #12147), we need a migration strategy for existing MLMD data (executions, artifacts, events) when upgrading to a KFP version without MLMD.

## Design
See `proposals/12147-mlmd-removal/database-migration-design.md` for complete design.

### Key Features
- **Idempotent migration** - Can run multiple times, migrates only delta
- **Dual execution modes** - CLI tool (manual) + API server integration (automatic)
- **95% code reuse** - Both modes use same migration engine
- **Zero downtime** - API server serves traffic during migration
- **Resumable** - Checkpoint-based recovery from interruptions

### Approach
This PR follows the design pattern from [proposal 11385](https://github.com/kubeflow/pipelines/tree/master/proposals/11385-literal-input-parameters).

**This is a design-only PR.** Implementation will follow in separate PR after design approval.

## File Changes
- ✅ `proposals/12147-mlmd-removal/database-migration-design.md` (new design doc)
- ✅ `proposals/12147-mlmd-removal/database-migration/README.md` (summary)
- ❌ No implementation code (`.go` files) - design only

## Testing Plan
See design document for testing strategy:
- Unit tests for transformers
- Integration tests with MLMD
- Load tests (1M+ entities)
- Multi-replica coordination tests

## Next Steps
After design approval:
1. Implement shared migration engine
2. Implement CLI tool
3. Implement API server integration
4. Testing and validation
```

## Validation Checklist

Before creating PR, verify:

- [ ] Only design documents included (no `.go` files)
- [ ] `database-migration-design.md` is complete and clear
- [ ] File structure is documented
- [ ] Migration strategy explained (idempotency, checkpoints)
- [ ] Both execution modes described (CLI + API server)
- [ ] Key transformations specified (exit handlers, cache fingerprints, metrics)
- [ ] PR description mentions this is design-only
- [ ] Commit follows conventional commits format
- [ ] DCO sign-off included

## FAQ

**Q: Why design-only, no implementation?**
A: Following 11385 pattern - get design approval first, then implement. Separates concerns and makes review easier.

**Q: Where's the migration code?**
A: Will be in follow-up PR. This PR only documents **what** will be implemented and **where** it will go.

**Q: Why two execution modes (CLI + API server)?**
A: Flexibility - large deployments want manual control, small deployments want automatic. Same code, different entry points.

**Q: Is the metrics table approach correct?**
A: Design stores metrics in artifacts table (Type=Metric, NumberValue field) instead of separate Metrics table. Simpler and matches protobuf schema. If reviewers prefer separate table, can adjust before implementation.

**Q: What happens after this PR merges?**
A: Implementation PR(s) will follow, implementing the design specified here.

## Contact

For questions about this proposal, contact @vmudadla or comment on the PR.
