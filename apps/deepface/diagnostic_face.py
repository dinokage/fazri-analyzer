#!/usr/bin/env python3
"""
Diagnostic script for face recognition mismatch debugging.
Run with: /Users/dinokage/dev/deepface-server/deepface/bin/python diagnostic_face.py
"""

import os
import sys

# Must be set before any TF/DeepFace import
os.environ["TF_USE_LEGACY_KERAS"] = "1"

# ─────────────────────────────────────────────────────────────
# 1. Read stored embeddings from Postgres
# ─────────────────────────────────────────────────────────────
print("=" * 70)
print("SECTION 1: Stored embeddings in Postgres")
print("=" * 70)

try:
    import psycopg
    conn = psycopg.connect("postgresql://deepface:deepface@localhost:5432/deepface")
    cur = conn.cursor()
    cur.execute(
        "SELECT id, img_name, model_name, detector_backend, aligned, l2_normalized, embedding "
        "FROM embeddings LIMIT 5"
    )
    rows = cur.fetchall()
    if not rows:
        print("WARNING: No rows found in embeddings table!")
    for r in rows:
        emb = r[6]
        print(f"id={r[0]} img_name={r[1]} model={r[2]} detector={r[3]} aligned={r[4]} l2={r[5]}")
        print(f"  embedding length  : {len(emb)}")
        print(f"  embedding[:5]     : {emb[:5]}")
        emb_min = min(emb)
        emb_max = max(emb)
        import statistics
        emb_mean = statistics.mean(emb)
        emb_stdev = statistics.stdev(emb)
        print(f"  min={emb_min:.6f}  max={emb_max:.6f}  mean={emb_mean:.6f}  stdev={emb_stdev:.6f}")
        is_healthy = emb_stdev > 0.01 and emb_min != emb_max
        print(f"  HEALTH: {'LOOKS HEALTHY (varied floats)' if is_healthy else 'SUSPICIOUS (near-constant or collapsed)'}")
        print()

    # Print distinct model/detector combos stored
    cur.execute(
        "SELECT DISTINCT model_name, detector_backend, aligned, l2_normalized, COUNT(*) "
        "FROM embeddings GROUP BY model_name, detector_backend, aligned, l2_normalized"
    )
    combos = cur.fetchall()
    print("Distinct (model, detector, aligned, l2_normalized) combos in DB:")
    for c in combos:
        print(f"  model={c[0]}  detector={c[1]}  aligned={c[2]}  l2={c[3]}  count={c[4]}")

    conn.close()
except Exception as e:
    print(f"ERROR connecting to Postgres: {e}")

# ─────────────────────────────────────────────────────────────
# 2. Config / .env inspection
# ─────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("SECTION 2: Config settings")
print("=" * 70)

print("\n--- .env file contents ---")
env_path = "/Users/dinokage/dev/deepface-server/.env"
try:
    with open(env_path) as f:
        print(f.read())
except FileNotFoundError:
    print("  .env not found")

print("--- config.py derived settings (via pydantic) ---")
sys.path.insert(0, "/Users/dinokage/dev/deepface-server")
try:
    # We import carefully without triggering TF
    from app.config import settings
    print(f"  model_name        : {settings.model_name}")
    print(f"  detector_backend  : {settings.detector_backend}")
    print(f"  distance_metric   : {settings.distance_metric}")
    print(f"  cosine_threshold  : {settings.cosine_threshold}")
    print(f"  enforce_detection : {settings.enforce_detection}")
    print(f"  l2_normalize      : {settings.l2_normalize}")
    print(f"  normalization     : {settings.normalization}")
    print(f"  postgres_uri      : {settings.deepface_postgres_uri}")
except Exception as e:
    print(f"ERROR loading config: {e}")

# ─────────────────────────────────────────────────────────────
# 3. fetch_all_embeddings SQL (static analysis summary)
# ─────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("SECTION 3: fetch_all_embeddings SQL query (from postgres.py)")
print("=" * 70)
print("""
The exact SQL executed by fetch_all_embeddings in
deepface/modules/database/postgres.py is:

    SELECT id, img_name, embedding
    FROM embeddings
    WHERE model_name = %s
      AND detector_backend = %s
      AND aligned = %s
      AND l2_normalized = %s
    ORDER BY id ASC;

Parameters passed:  (model_name, detector_backend, aligned, l2_normalized)
""")

# ─────────────────────────────────────────────────────────────
# 4. Generate a fresh embedding and compare
# ─────────────────────────────────────────────────────────────
print("=" * 70)
print("SECTION 4: Fresh embedding vs stored embedding (cosine distance)")
print("=" * 70)

TEST_IMAGE = "/Users/dinokage/dev/deepface-server/deepface/insightface/data/images/Tom_Hanks_54745.png"

# Pull the first stored embedding for comparison
try:
    conn2 = psycopg.connect("postgresql://deepface:deepface@localhost:5432/deepface")
    cur2 = conn2.cursor()
    cur2.execute(
        "SELECT id, img_name, model_name, detector_backend, aligned, l2_normalized, embedding "
        "FROM embeddings LIMIT 1"
    )
    ref_row = cur2.fetchone()
    conn2.close()

    if ref_row is None:
        print("No stored embeddings to compare against.")
        stored_emb = None
        stored_model = "Buffalo_L"
        stored_detector = "mtcnn"
        stored_aligned = True
        stored_l2 = False
    else:
        stored_emb = ref_row[6]
        stored_model = ref_row[2]
        stored_detector = ref_row[3]
        stored_aligned = ref_row[4]
        stored_l2 = ref_row[5]
        print(f"Reference row id={ref_row[0]}  img={ref_row[1]}")
        print(f"  Using model={stored_model}  detector={stored_detector}  aligned={stored_aligned}  l2={stored_l2}")
except Exception as e:
    print(f"ERROR fetching reference embedding: {e}")
    stored_emb = None
    stored_model = "Buffalo_L"
    stored_detector = "mtcnn"
    stored_aligned = True
    stored_l2 = False

print("\nLoading DeepFace (this may take a moment)...")
try:
    from deepface import DeepFace

    print(f"Generating embedding for: {TEST_IMAGE}")
    print(f"  model_name={stored_model}  detector_backend={stored_detector}")
    print(f"  normalization=raw  l2_normalize={stored_l2}  align={stored_aligned}")

    results = DeepFace.represent(
        img_path=TEST_IMAGE,
        model_name=stored_model,
        detector_backend=stored_detector,
        enforce_detection=False,          # test image may not have a face detected perfectly
        align=stored_aligned,
        normalization="raw",
        l2_normalize=stored_l2,
    )

    if results:
        fresh_emb = results[0]["embedding"]
        print(f"\nFresh embedding length : {len(fresh_emb)}")
        print(f"Fresh embedding[:5]    : {fresh_emb[:5]}")
        import statistics as st
        fe_min = min(fresh_emb)
        fe_max = max(fresh_emb)
        fe_mean = st.mean(fresh_emb)
        fe_stdev = st.stdev(fresh_emb)
        print(f"min={fe_min:.6f}  max={fe_max:.6f}  mean={fe_mean:.6f}  stdev={fe_stdev:.6f}")
        fresh_healthy = fe_stdev > 0.01 and fe_min != fe_max
        print(f"HEALTH: {'LOOKS HEALTHY' if fresh_healthy else 'SUSPICIOUS'}")

        if stored_emb is not None:
            # Manual cosine distance
            import math
            def cosine_distance(a, b):
                dot = sum(x * y for x, y in zip(a, b))
                norm_a = math.sqrt(sum(x * x for x in a))
                norm_b = math.sqrt(sum(x * x for x in b))
                if norm_a == 0 or norm_b == 0:
                    return 1.0
                return 1.0 - dot / (norm_a * norm_b)

            dist = cosine_distance(stored_emb, fresh_emb)
            print(f"\nCosine distance (stored vs fresh from test image): {dist:.6f}")
            print("(Note: these are different people/images so a high distance is expected)")
            print("(Same-person threshold is typically 0.40 - 0.55)")
    else:
        print("No embedding results returned from DeepFace.represent()")

except Exception as e:
    print(f"ERROR generating fresh embedding: {e}")
    import traceback
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────
# 5. Mismatch analysis
# ─────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("SECTION 5: Mismatch analysis")
print("=" * 70)

try:
    from app.config import settings as cfg

    print(f"\nServer settings.normalization   : '{cfg.normalization}'")
    print(f"Server settings.l2_normalize    : {cfg.l2_normalize}")
    print(f"Server settings.detector_backend: '{cfg.detector_backend}'")
    print(f"Server settings.model_name      : '{cfg.model_name}'")
    print(f"Server settings.cosine_threshold: {cfg.cosine_threshold}")

    print(f"\n.env COSINE_THRESHOLD           : 0.55 (raw .env value)")
    print(f"config.py default threshold     : 0.40")
    print(f"Effective threshold (pydantic)  : {cfg.cosine_threshold}")

    print(f"\nDB stored detector_backend      : '{stored_detector}'")
    print(f"DB stored l2_normalized         : {stored_l2}")

    mismatch_found = False

    if cfg.detector_backend != stored_detector:
        print(f"\n!!! MISMATCH: server detector_backend='{cfg.detector_backend}' "
              f"but stored rows have detector_backend='{stored_detector}'")
        print("    fetch_all_embeddings filters by detector_backend, so a mismatch = ZERO results returned!")
        mismatch_found = True

    if cfg.l2_normalize != stored_l2:
        print(f"\n!!! MISMATCH: server l2_normalize={cfg.l2_normalize} "
              f"but stored rows have l2_normalized={stored_l2}")
        print("    fetch_all_embeddings filters by l2_normalized, so a mismatch = ZERO results returned!")
        mismatch_found = True

    if cfg.model_name != stored_model:
        print(f"\n!!! MISMATCH: server model_name='{cfg.model_name}' "
              f"but stored rows have model_name='{stored_model}'")
        mismatch_found = True

    if cfg.normalization != "raw":
        print(f"\n!!! NORMALIZATION WARNING: server normalization='{cfg.normalization}' "
              f"but registration may have used a different normalization.")
        print("    Buffalo_L / InsightFace requires raw [0,255] input.")
        mismatch_found = True

    if not mismatch_found:
        print("\nNo obvious parameter mismatch detected between server config and stored rows.")
        print("The mismatch may be due to threshold being too tight, or the query face quality.")

    print()
    print("--- SUMMARY ---")
    print(f".env does NOT set L2_NORMALIZE or NORMALIZATION - these fall back to config.py defaults:")
    print(f"  l2_normalize = False (default)")
    print(f"  normalization = 'raw' (default)")
    print(f"config.py cosine_threshold default is 0.40; .env sets it to 0.55")
    print(f"Effective cosine_threshold in server: {cfg.cosine_threshold}")

except Exception as e:
    print(f"ERROR in mismatch analysis: {e}")
    import traceback
    traceback.print_exc()

print()
print("Diagnostic complete.")
