# Database Migration Proposal - Commit Checklist

Following the pattern from [proposal 11385](https://github.com/kubeflow/pipelines/tree/master/proposals/11385-literal-input-parameters), this is a **design-only PR** with no implementation code.

## ✅ Files to Commit (Design Only)

### Core Design Documents

1. **`proposals/12147-mlmd-removal/database-migration/README.md`**
   - Summary and quick reference
   - File structure overview
   - Usage examples

2. **`proposals/12147-mlmd-removal/database-migration-design.md`**
   - Complete design specification
   - Architecture diagrams
   - MLMD entity transformations
   - Execution modes (CLI vs API server)
   - Idempotency strategy
   - Migration phases

3. **`proposals/12147-mlmd-removal/schema_changes.sql`**
   - Database schema reference
   - Shows new tables (artifacts, artifact_tasks, tasks)
   - Migration tracking tables

4. **`proposals/12147-mlmd-removal/test_plan.md`** (optional)
   - Testing strategy
   - If already exists and relevant

## ❌ Files NOT to Commit (Remove These)

### Implementation Code (Will be in follow-up PR)
- ❌ `backend/src/apiserver/migration/*` (any Go files)
- ❌ `backend/cmd/mlmd-migrate/*` (any Go files)
- ❌ `backend/src/apiserver/model/migration_*.go` (any Go files)

### Redundant Design Documents (Too Many Versions)
- ❌ `api-server-integration-design.md` (merged into main design)
- ❌ `cli-tool-design.md` (merged into main design)
- ❌ `migration-design.md` (old version)
- ❌ `migration-design-v2.md` (old version)
- ❌ `migration-design-v3.md` (old version)
- ❌ `migration-design-standalone.md` (old version)
- ❌ `migration-design-summary.md` (redundant)
- ❌ `migration-quick-reference.md` (redundant)
- ❌ `migration-implementation-guide.md` (implementation, not design)
- ❌ `PR_SUMMARY.md` (internal doc, not needed for proposal)
- ❌ `README_MIGRATIONS.md` (navigation for many docs - not needed)

### Keep Existing Files
- ✅ `README.md` (main MLMD removal proposal - don't touch)
- ✅ `design-details.md` (upstream MLMD removal design - don't touch)
- ✅ `test_plan.md` (existing test plan - keep if relevant)

## Final Directory Structure

After cleanup, the proposal should look like:

```
proposals/12147-mlmd-removal/
├── README.md                           # Existing - main proposal
├── design-details.md                   # Existing - upstream design
├── test_plan.md                        # Existing - test strategy
├── schema_changes.sql                  # Existing - DB schema
│
├── database-migration/                 # NEW - this proposal
│   └── README.md                       # Migration proposal summary
│
└── database-migration-design.md        # NEW - complete design doc
```

## Git Commands to Clean Up

```bash
cd /home/vmudadla/workspace/data-science-pipelines

# Remove redundant design documents
rm proposals/12147-mlmd-removal/api-server-integration-design.md
rm proposals/12147-mlmd-removal/cli-tool-design.md
rm proposals/12147-mlmd-removal/migration-design.md
rm proposals/12147-mlmd-removal/migration-design-v2.md
rm proposals/12147-mlmd-removal/migration-design-v3.md
rm proposals/12147-mlmd-removal/migration-design-standalone.md
rm proposals/12147-mlmd-removal/migration-design-summary.md
rm proposals/12147-mlmd-removal/migration-quick-reference.md
rm proposals/12147-mlmd-removal/migration-implementation-guide.md
rm proposals/12147-mlmd-removal/PR_SUMMARY.md
rm proposals/12147-mlmd-removal/README_MIGRATIONS.md

# Stage new files
git add proposals/12147-mlmd-removal/database-migration/
git add proposals/12147-mlmd-removal/database-migration-design.md
```

## PR Description Template

```markdown
# Database Migration Design for MLMD Removal

## Summary
Design document for migrating MLMD data to native KFP tables.

## Motivation
As part of MLMD removal, we need a migration strategy for existing MLMD data.

## Design
See `proposals/12147-mlmd-removal/database-migration-design.md` for complete design.

### Key Features
- Idempotent migration (can run multiple times)
- Dual execution modes (CLI tool + API server integration)
- 95% code reuse between modes
- Zero-downtime migration
- Resumable on interruption

### Approach
Follows design pattern from [proposal 11385](https://github.com/kubeflow/pipelines/tree/master/proposals/11385-literal-input-parameters).

This is a **design-only PR**. Implementation will follow in separate PR.

## Testing
- Unit tests for transformers
- Integration tests with MLMD
- Load tests (1M+ entities)
```

## Verification Checklist

Before committing, verify:

- [ ] Only design documents included (no `.go` files)
- [ ] Single clear design document (not multiple versions)
- [ ] File structure documented
- [ ] Usage examples provided
- [ ] Implementation plan outlined
- [ ] Follows 11385 pattern (design-only, implementation later)
- [ ] PR description mentions this is design-only
