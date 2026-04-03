# FAZRI Technical Debt Cleanup — Claude Code Runbook

**Branch**: `core-feature-speedrun` on `github.com/dinokage/fazri-analyzer`
**Date**: 2026-04-03
**Objective**: Eliminate all dead code, stale artifacts, and overlapping systems. Leave the codebase with exactly one authoritative path for every capability.

---

## Rules for This Runbook

1. Execute phases sequentially. Each phase depends on the previous one completing cleanly.
2. After every deletion or modification, run the verification command provided. Do not proceed if verification fails.
3. Do not refactor working code. This is a cleanup operation, not a rewrite.
4. Commit after each phase with the exact commit message provided.
5. If a step is ambiguous, stop and ask — do not guess.

---

## Phase 0: Binary Artifact Purge

**Goal**: Remove ~100MB of files that should never have been committed to git.

### Step 0.1 — Delete stale ML pickle files

The code that consumed these (`ml_predictor.py`, `train_predictor.py`) was already deleted. These are orphaned binary artifacts.

```
DELETE all files matching: backend/models/predictor_*.pkl
```

There are 34 pickle files. Delete every one. Do NOT delete any `.py` files in `backend/models/`.

**Verify**:
```bash
ls backend/models/predictor_*.pkl 2>&1 | wc -l
# Expected: 0 (or "No such file" error)
```

### Step 0.2 — Add augmented data to .gitignore

`backend/augmented/` contains 85MB of synthetic CSV data. It should not be tracked in git. The data should remain on disk for local development but must be excluded from commits.

Add these lines to the root `.gitignore`:
```
# Synthetic / augmented data (large CSVs, not for version control)
backend/augmented/
```

Then untrack the files (without deleting them from disk):
```bash
git rm -r --cached backend/augmented/
```

**Verify**:
```bash
git status backend/augmented/ 2>&1 | head -5
# Expected: files listed as "deleted" in staging (untracked, not on disk deleted)
du -sh backend/augmented/
# Expected: ~85M (files still exist on disk)
```

### Step 0.3 — Add other binary patterns to .gitignore

Append these to the root `.gitignore` if not already present:
```
# ML model artifacts
*.pkl
*.pickle
*.h5
*.pt
*.onnx

# Large data files
*.csv.gz
```

### Step 0.4 — Delete stale config example

```
DELETE: backend/config.example.py
```

This is a legacy 18-line file superseded by `backend/config/__init__.py` and the `.env.prod.example`.

**Verify**:
```bash
test ! -f backend/config.example.py && echo "PASS" || echo "FAIL"
```

### Step 0.5 — Delete old GitLab CI file

```
DELETE: old-gitlab-ci.yml
```

The project uses Jenkins. This 40-line file is dead.

**Verify**:
```bash
test ! -f old-gitlab-ci.yml && echo "PASS" || echo "FAIL"
```

**Commit**: `chore: purge stale binary artifacts and untrack augmented data`

---

## Phase 1: Delete Dead Anomaly Detection Systems

**Goal**: The authoritative anomaly detection path is `backend/services/deepface_anomaly.py` (the stateless rule engine), invoked by `EventIngestionService`. Two older systems exist in parallel and must be removed along with all their consumers.

### Step 1.1 — Delete the old anomaly detection services

```
DELETE: backend/services/anomaly_detection.py          (541 lines)
DELETE: backend/services/entity_anomaly_detection.py   (915 lines)
```

These are the pre-refactor anomaly systems. They have their own DB queries, their own rule logic, and their own interfaces — all duplicated by the new `deepface_anomaly.py` + `EventIngestionService` pipeline.

**Verify**:
```bash
test ! -f backend/services/anomaly_detection.py && echo "PASS" || echo "FAIL"
test ! -f backend/services/entity_anomaly_detection.py && echo "PASS" || echo "FAIL"
```

### Step 1.2 — Delete the old anomaly routes

```
DELETE: backend/anomaly_routes.py                      (the file at backend root, ~350+ lines)
```

This file imports both deleted services. Its endpoints are superseded by the alert system routes (`routes/alert_routes.py`) and the new events/system routes.

**Verify**:
```bash
test ! -f backend/anomaly_routes.py && echo "PASS" || echo "FAIL"
```

### Step 1.3 — Remove anomaly_routes from main.py

In `backend/main.py`, make these changes:

**Change this line**:
```python
import entity_routes, graph_routes, anomaly_routes, chat_routes
```
**To**:
```python
import entity_routes, graph_routes, chat_routes
```

**Delete this line**:
```python
app.include_router(anomaly_routes.router)
```

**Verify**:
```bash
grep -n "anomaly_routes" backend/main.py
# Expected: no output (zero matches)
```

### Step 1.4 — Delete debug/diagnostic scripts that depend on deleted services

These scripts import the deleted anomaly services and have no value in the new architecture:

```
DELETE: backend/debug_zero_anomalies.py       (272 lines — imports AnomalyDetectionService)
DELETE: backend/diagnose_anomalies.py         (250 lines — imports AnomalyDetectionService)
DELETE: backend/test_service_directly.py      (87 lines — imports AnomalyDetectionService)
DELETE: backend/cache_anomalies.py            (134 lines — imports AnomalyDetectionService)
```

**Verify**:
```bash
for f in debug_zero_anomalies.py diagnose_anomalies.py test_service_directly.py cache_anomalies.py; do
  test ! -f "backend/$f" && echo "PASS: $f" || echo "FAIL: $f"
done
```

### Step 1.5 — Delete stale test script for old anomaly system

```
DELETE: backend/test_entity_endpoint.sh
```

This shell script tests the old anomaly endpoints that no longer exist.

**Verify**:
```bash
test ! -f backend/test_entity_endpoint.sh && echo "PASS" || echo "FAIL"
```

### Step 1.6 — Full-codebase import verification

After all deletions, verify no remaining Python file imports the deleted modules:

```bash
grep -rn "from services.anomaly_detection\|from services.entity_anomaly_detection\|import anomaly_detection\|import entity_anomaly_detection" backend/ --include="*.py" | grep -v "__pycache__"
```

**Expected**: Zero matches.

If `backend/services/chatbot/tool_executor.py` still references them, handle it in Phase 2.

**Commit**: `chore: remove legacy anomaly detection systems — deepface_anomaly.py is now authoritative`

---

## Phase 2: Chatbot Cleanup

**Goal**: The chatbot tool executor is 1,667 lines and imports deleted services. It needs to be stripped down to remove dead references. The chatbot is NOT pilot-critical and should not block deployment.

### Step 2.1 — Audit chatbot tool_executor.py imports

Open `backend/services/chatbot/tool_executor.py` and identify all imports that reference deleted modules:

```bash
grep -n "from services.anomaly_detection\|from services.entity_anomaly_detection\|from services.ml_predictor\|from services.pattern_detection\|from services.spatial_forecasting" backend/services/chatbot/tool_executor.py
```

### Step 2.2 — Remove dead imports and methods from tool_executor.py

For every import line found in Step 2.1:
1. Delete the import line.
2. Find all methods/functions in the file that use the imported class.
3. Either delete those methods entirely OR replace their bodies with:
```python
raise NotImplementedError("This tool is disabled pending pipeline migration.")
```

Do NOT rewrite the chatbot architecture. Just remove the dead references so the file compiles.

### Step 2.3 — Verify tool_executor.py compiles

```bash
cd backend && python -c "from services.chatbot.tool_executor import *" 2>&1
```

**Expected**: No ImportError. Warnings are acceptable.

If it fails because of missing graph_builder or other dependencies, those are pre-existing issues — do NOT fix them in this phase. Just ensure no import references a file that was deleted in Phase 1.

**Commit**: `chore: remove dead anomaly/ML imports from chatbot tool executor`

---

## Phase 3: Dead Script Cleanup

**Goal**: Remove scripts that reference deleted services, test non-existent features, or have been superseded.

### Step 3.1 — Delete superseded scripts

```
DELETE: backend/scripts/train_predictor.py         (if still exists — should already be gone)
DELETE: backend/scripts/test_predictor.py           (tests the deleted ML predictor)
DELETE: backend/scripts/realtime_data_simulator.py  (718 lines — superseded by simulators/ directory)
DELETE: backend/scripts/debug_columns.py            (one-off debug script)
DELETE: backend/scripts/test_fusion.py              (tests old fusion pipeline)
DELETE: backend/scripts/test_timeline.py            (tests old timeline service)
```

### Step 3.2 — Delete the legacy eSSL simulator

```
DELETE entire directory: backend/simulators/essl_simulator/
```

This contains `generate_data.py`, `init.sql`, and `test_connector.py` for a biometric device simulator that predates the Hikvision/Aruba simulator architecture. It is not referenced by any active code.

**Verify**:
```bash
grep -rn "essl_simulator\|essl" backend/ --include="*.py" | grep -v "__pycache__" | grep -v "augmented"
# Expected: zero matches (or only comments)
```

### Step 3.3 — Evaluate remaining scripts

These scripts should be KEPT (they are actively useful):
- `backend/scripts/sample_zones.py` — zone data used by zone_matrix.py (imported at runtime)
- `backend/scripts/sap_csv_import.py` — SAP CSV import utility
- `backend/scripts/ingest_real_data.py` — data ingestion helper
- `backend/scripts/run_auth_tests.sh` — auth test runner

These scripts reference `graph_builder` and should be evaluated:
- `backend/scripts/ingest_graph.py` — imports CampusGraphBuilder. **KEEP** if Neo4j graph ingestion is still used. Otherwise **DELETE**.
- `backend/scripts/verify_ingestion.py` — imports get_graph_builder. **KEEP** if Neo4j is still used. Otherwise **DELETE**.
- `backend/scripts/check_data_status.py` — imports get_graph_builder. **KEEP** if Neo4j is still used. Otherwise **DELETE**.
- `backend/scripts/update_zone_capacities.py` — check if it references deleted modules. If clean, **KEEP**.

Decision rule: Neo4j is still in the architecture as a read-only graph sidecar. Scripts that interact with it should be KEPT unless they import deleted modules. If they import deleted modules, fix the import or delete the script.

**Verify**:
```bash
ls backend/scripts/
# Should contain only: sample_zones.py, sap_csv_import.py, ingest_real_data.py, run_auth_tests.sh,
# and optionally: ingest_graph.py, verify_ingestion.py, check_data_status.py, update_zone_capacities.py
```

**Commit**: `chore: remove superseded scripts and legacy eSSL simulator`

---

## Phase 4: Dead Documentation Cleanup

**Goal**: Remove markdown files that document deleted features or contain outdated architecture descriptions.

### Step 4.1 — Delete backend-level stale docs

These documents describe the old anomaly detection system, the old entity routes, or provide diagnostic guides for deleted features:

```
DELETE: backend/CHECK_STATUS.md
DELETE: backend/DIAGNOSIS_REPORT.md
DELETE: backend/ENTITY_ANOMALY_API_GUIDE.md
DELETE: backend/ZONES_AND_ANOMALIES.md
```

### Step 4.2 — Evaluate backend docs to keep

- `backend/QUICK_START_GUIDE.md` — **Review and update** if it references deleted services/routes. If >50% of the content is stale, **DELETE** and replace later with an accurate guide.
- `backend/alerts-guide.md` — **KEEP** if it accurately describes the current alert system. **DELETE** if it documents the old anomaly routes.

### Step 4.3 — Delete root-level stale docs

```
DELETE: AI-chatbot.md              (972 lines — chatbot feature doc, not pilot-critical)
DELETE: ALERTS.md                  (1531 lines — documents old alert architecture)
DELETE: ALERTS_FRONTEND_PLAN.md    (547 lines — old frontend plan)
DELETE: TODO.md                    (757 lines — stale todo list)
DELETE: GIT_CLEANUP_SUMMARY.md    (208 lines — one-time cleanup summary, no longer relevant)
```

### Step 4.4 — Evaluate root docs to keep

- `CREDENTIAL_ROTATION_GUIDE.md` — **KEEP** (operational security doc, still valid)
- `SECURITY_QUICK_START.md` — **KEEP** (operational security doc, still valid)
- `README.md` — **KEEP but flag for update** (likely references deleted features)

### Step 4.5 — Delete the stale notebook

```
DELETE: backend/notebooks/01_data_exploration.ipynb
```

This notebook was created during the CSV/pandas era and explores the augmented data. It references patterns that no longer exist in the codebase.

**Verify**:
```bash
find backend/notebooks -type f | wc -l
# Expected: 0
# If the directory is now empty, delete it:
rmdir backend/notebooks 2>/dev/null
```

**Commit**: `chore: remove stale documentation and notebooks`

---

## Phase 5: Schema & Model Cleanup

**Goal**: Remove dead code from active files without changing behavior.

### Step 5.1 — Remove NotImplementedError stubs from SensorEvent

In `backend/models/schemas/sensor_events.py`, delete these three methods entirely (lines ~146–181):
- `from_hikvision_access()`
- `from_aruba_association()`
- `from_deepface_match()`

These are factory stubs that raise `NotImplementedError`. The actual conversion happens in the connector classes (`hikvision_client.py`, `aruba_client.py`, `deepface_routes.py`). The stubs are misleading.

Also delete the `# Week 2 connectors` comment block above them.

**Verify**:
```bash
grep -n "NotImplementedError\|from_hikvision\|from_aruba\|from_deepface_match" backend/models/schemas/sensor_events.py
# Expected: zero matches
```

### Step 5.2 — Verify SensorEvent still imports cleanly

```bash
cd backend && python -c "from models.schemas.sensor_events import SensorEvent, ResolvedEvent; print('OK')"
```

**Expected**: `OK`

**Commit**: `chore: remove dead factory stubs from SensorEvent schema`

---

## Phase 6: Fix the main.py Shutdown Bug

**Goal**: Fix the task cancellation logic so all background tasks are properly awaited on shutdown.

### Step 6.1 — Fix the lifespan shutdown block

In `backend/main.py`, the current shutdown block (approximately lines 217-228) has a bug. The `await _batch_sync_task` is misplaced inside the aruba cancel block, and the hikvision/aruba tasks are never awaited after cancellation.

**Replace the entire shutdown block** (everything after `yield` and before `logger.info("Shutting down...")`):

```python
    yield

    # Shutdown — cancel background tasks cleanly
    tasks_to_cancel = []
    if _batch_sync_task and not _batch_sync_task.done():
        _batch_sync_task.cancel()
        tasks_to_cancel.append(_batch_sync_task)
    if _hikvision_task and not _hikvision_task.done():
        _hikvision_task.cancel()
        tasks_to_cancel.append(_hikvision_task)
    if _aruba_task and not _aruba_task.done():
        _aruba_task.cancel()
        tasks_to_cancel.append(_aruba_task)

    for task in tasks_to_cancel:
        try:
            await task
        except asyncio.CancelledError:
            pass

    logger.info("Shutting down Fazri Analyzer API...")
```

**Verify**:
```bash
cd backend && python -c "
import ast, sys
with open('main.py') as f:
    tree = ast.parse(f.read())
print('Syntax OK')
"
```

**Expected**: `Syntax OK`

**Commit**: `fix: properly cancel and await all background tasks on shutdown`

---

## Phase 7: Verify Full System Integrity

**Goal**: Ensure the application starts and all routes register after cleanup.

### Step 7.1 — Check for broken imports across the entire backend

```bash
cd backend && python -c "
import importlib, sys, os
sys.path.insert(0, '.')
errors = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', 'augmented', 'notebooks', 'simulators')]
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            module_path = os.path.join(root, f).replace('./', '').replace('/', '.').replace('.py', '')
            try:
                importlib.import_module(module_path)
            except Exception as e:
                errors.append(f'{module_path}: {type(e).__name__}: {e}')

if errors:
    print(f'FAIL: {len(errors)} import errors:')
    for e in errors:
        print(f'  {e}')
else:
    print('PASS: all modules import cleanly')
"
```

This will likely show some import errors for modules that require running services (DB, Redis, Neo4j). That is expected. What you are looking for is `ModuleNotFoundError` — those indicate broken references to deleted files.

### Step 7.2 — Verify main.py can parse

```bash
cd backend && python -c "import ast; ast.parse(open('main.py').read()); print('PASS')"
```

### Step 7.3 — Check that no Python file references a deleted module

```bash
cd /path/to/fazri-analyzer

echo "=== Checking for references to deleted files ==="
DELETED_MODULES=(
  "services.anomaly_detection"
  "services.entity_anomaly_detection"
  "services.ml_predictor"
  "services.pattern_detection"
  "services.spatial_forecasting"
)

FAIL=0
for mod in "${DELETED_MODULES[@]}"; do
  matches=$(grep -rn "$mod" backend/ --include="*.py" | grep -v "__pycache__" | wc -l)
  if [ "$matches" -gt 0 ]; then
    echo "FAIL: $mod still referenced ($matches matches)"
    grep -rn "$mod" backend/ --include="*.py" | grep -v "__pycache__"
    FAIL=1
  fi
done

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: no references to deleted modules"
fi
```

**Expected**: `PASS: no references to deleted modules`

### Step 7.4 — Line count reduction audit

```bash
echo "=== Post-cleanup line counts ==="
find backend/ -name "*.py" -not -path "*/augmented/*" -not -path "*/__pycache__/*" | xargs wc -l | tail -1
echo "---"
find backend/ -name "*.md" | xargs wc -l 2>/dev/null | tail -1
echo "---"
find . -maxdepth 1 -name "*.md" | xargs wc -l | tail -1
```

Record the before/after for the commit message.

**Commit**: `chore: verify system integrity after technical debt cleanup`

---

## Phase 8: .gitignore Finalization and Commit Hygiene

### Step 8.1 — Review the full .gitignore

Ensure the root `.gitignore` includes at minimum:
```
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.eggs/
dist/
build/
*.egg
.venv/
venv/

# ML artifacts
*.pkl
*.pickle
*.h5
*.pt
*.onnx

# Synthetic data
backend/augmented/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Environment
.env
.env.*
!.env.prod.example
!env.example

# OS
.DS_Store
Thumbs.db

# Node
node_modules/
.next/
out/

# Credentials (belt-and-suspenders)
*credentials*.json
!*credentials*.json.example

# Docker
*.log
```

### Step 8.2 — Verify nothing sensitive is tracked

```bash
git ls-files | grep -i "credentials\|secret\|\.env$\|\.pem\|\.key" | grep -v "example\|\.gitignore"
```

**Expected**: Only `backend/gcp-credentials.json` (which is an empty file). If it is empty (0 bytes), leave it. If it contains real credentials, untrack it immediately.

```bash
wc -c backend/gcp-credentials.json
# Expected: 0 (empty file)
```

**Commit**: `chore: finalize .gitignore and verify no sensitive files tracked`

---

## Summary of Deletions

After all phases complete, the following files/directories should no longer exist:

### Files Deleted
| File | Reason | Lines Removed |
|------|--------|---------------|
| `backend/models/predictor_*.pkl` (34 files) | Orphaned ML artifacts | ~15MB binary |
| `backend/services/anomaly_detection.py` | Superseded by deepface_anomaly.py | 541 |
| `backend/services/entity_anomaly_detection.py` | Superseded by deepface_anomaly.py | 915 |
| `backend/anomaly_routes.py` | Consumed deleted services | ~350 |
| `backend/debug_zero_anomalies.py` | Debug script for deleted system | 272 |
| `backend/diagnose_anomalies.py` | Debug script for deleted system | 250 |
| `backend/test_service_directly.py` | Test for deleted system | 87 |
| `backend/cache_anomalies.py` | Cache script for deleted system | 134 |
| `backend/test_entity_endpoint.sh` | Tests deleted endpoints | ~50 |
| `backend/config.example.py` | Superseded by config/__init__.py | 18 |
| `backend/scripts/test_predictor.py` | Tests deleted ML predictor | ~85 |
| `backend/scripts/realtime_data_simulator.py` | Superseded by simulators/ | 718 |
| `backend/scripts/debug_columns.py` | One-off debug script | ~30 |
| `backend/scripts/test_fusion.py` | Tests old pipeline | ~100 |
| `backend/scripts/test_timeline.py` | Tests old timeline | ~50 |
| `backend/simulators/essl_simulator/` | Legacy biometric simulator | ~420 |
| `backend/notebooks/01_data_exploration.ipynb` | Stale notebook | ~200 |
| `backend/CHECK_STATUS.md` | Stale doc | 194 |
| `backend/DIAGNOSIS_REPORT.md` | Stale doc | 75 |
| `backend/ENTITY_ANOMALY_API_GUIDE.md` | Documents deleted API | 199 |
| `backend/ZONES_AND_ANOMALIES.md` | Stale doc | 422 |
| `AI-chatbot.md` | Not pilot-critical | 972 |
| `ALERTS.md` | Documents old architecture | 1531 |
| `ALERTS_FRONTEND_PLAN.md` | Stale plan | 547 |
| `TODO.md` | Stale todo | 757 |
| `GIT_CLEANUP_SUMMARY.md` | One-time summary | 208 |
| `old-gitlab-ci.yml` | Dead CI config | 40 |

### Files Modified
| File | Change |
|------|--------|
| `backend/main.py` | Remove anomaly_routes import + router; fix shutdown task cancellation |
| `backend/services/chatbot/tool_executor.py` | Remove dead imports to deleted anomaly/ML services |
| `backend/models/schemas/sensor_events.py` | Remove 3 NotImplementedError factory stubs |
| `.gitignore` | Add augmented/, *.pkl, and other patterns |

### Estimated Impact
- **~100MB of binary data** removed from tracking
- **~7,000+ lines of dead Python code** deleted
- **~5,000+ lines of stale markdown** deleted
- **Zero behavior changes** to the running system
- **One bug fix** (shutdown task cancellation)

---

## What This Does NOT Cover (Deliberate Exclusions)

These are real issues but are NOT cleanup tasks — they are architecture decisions that need separate planning:

1. **Monorepo restructuring** (root-level Next.js → `apps/frontend`, `apps/backend`). This is a repo reorganization, not a cleanup. Do it when the team grows.

2. **Alembic migration setup**. The hand-rolled migrations work. Switch to Alembic before the next schema change, not as a cleanup task.

3. **DeepFace routes refactor** (1,218 lines). The routes ARE using the new EventIngestionService pipeline. The file is large but functional. Refactor when adding new camera features, not now.

4. **Graph builder consolidation** (graph_builder.py vs cctv_graph_service.py). Both are actively used for different graph operations. Consolidate when Neo4j patterns stabilize.

5. **SAML 2.0 SSO implementation**. This is a new feature, not debt.

6. **Alert system deduplication** (alert_service.py, staff_service.py, etc.). These are active and working. Refactor later.
