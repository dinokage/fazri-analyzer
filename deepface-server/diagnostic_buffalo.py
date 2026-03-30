"""
Diagnostic script for Buffalo_L face recognition pipeline.
Investigates normalization bugs and database query mismatches.
"""
import sys
import numpy as np
import cv2

print("=" * 70)
print("BUFFALO_L PIPELINE DIAGNOSTIC")
print("=" * 70)

# ── 1. Create a synthetic face-like image ────────────────────────────────────
print("\n[1] Creating synthetic face image (224x224 RGB, uint8)...")
img = np.zeros((224, 224, 3), dtype=np.uint8)
# Skin-tone background
img[:] = [180, 140, 110]
# Oval face shape (lighter)
cv2.ellipse(img, (112, 112), (80, 100), 0, 0, 360, (220, 185, 155), -1)
# Eyes
cv2.circle(img, (80, 95), 12, (40, 40, 40), -1)
cv2.circle(img, (144, 95), 12, (40, 40, 40), -1)
# Nose
cv2.ellipse(img, (112, 130), (10, 14), 0, 0, 360, (190, 155, 125), -1)
# Mouth
cv2.ellipse(img, (112, 158), (25, 10), 0, 0, 180, (160, 80, 80), -1)

test_img_path = "/tmp/test_face.jpg"
# save as BGR (cv2 default) – DeepFace loads as BGR
cv2.imwrite(test_img_path, img[:, :, ::-1])   # img is RGB → flip to BGR for cv2
print(f"   Saved to {test_img_path}")
print(f"   Pixel range: [{img.min()}, {img.max()}]  dtype={img.dtype}")

# ── 2. Simulate the exact preprocessing pipeline ─────────────────────────────
print("\n[2] Simulating pipeline stages manually...")

# DeepFace loads image as BGR via cv2
loaded_bgr = cv2.imread(test_img_path)   # uint8 BGR
print(f"   After load (BGR uint8): min={loaded_bgr.min()}, max={loaded_bgr.max()}")

# detection.extract_faces → returns RGB float [0,1]  (done by resize_image)
# representation.py line 173: img = img[:, :, ::-1]  (RGB→BGR)
# preprocessing.resize_image → scales to [0,1] float32

# Let's replicate resize_image output
img_rgb = loaded_bgr[:, :, ::-1].astype(np.float32) / 255.0  # [0,1] RGB
img_bgr_for_model = img_rgb[:, :, ::-1]                       # back to BGR [0,1]
img_4d = np.expand_dims(img_bgr_for_model, axis=0)            # (1,224,224,3)
# resize to 112x112 (Buffalo_L input)
img_112 = cv2.resize(img_bgr_for_model, (112, 112))
img_4d_112 = np.expand_dims(img_112, axis=0).astype(np.float32)

print(f"   After resize_image (BGR float32 [0,1]): min={img_4d_112.min():.4f}, max={img_4d_112.max():.4f}")

# normalization="base" → returns as-is  [0,1]
img_base = img_4d_112.copy()
print(f"\n   [normalization='base'] pixel range: [{img_base.min():.4f}, {img_base.max():.4f}]")

# normalization="raw" → img *= 255  → [0,255]
img_raw = img_4d_112.copy()
img_raw *= 255
print(f"   [normalization='raw']  pixel range: [{img_raw.min():.2f}, {img_raw.max():.2f}]")

# ── 3. What Buffalo_L.preprocess() does ──────────────────────────────────────
print("\n[3] Buffalo_L.preprocess() does: img[:,:,:,::-1]  (swap channel axis -1)")
print("   i.e. it SWAPS BGR→RGB (or RGB→BGR, same operation)")
print("   This is applied AFTER normalize_input() in the pipeline.")
print()
print("   Pipeline for 'base':")
print("     load(BGR) → extract_faces(RGB [0,1]) → rgb2bgr → resize→[0,1] → base(noop) → preprocess(bgr2rgb) → get_feat(swapRB=True)")
print("     get_feat receives: RGB [0,1]  BUT expects [0,255] → divides by 127.5 → all values ~0-0.008 → near-zero input → GARBAGE embeddings")
print()
print("   Pipeline for 'raw':")
print("     ... same up to normalize... → raw(*=255) → [0,255] BGR → preprocess(bgr2rgb) → RGB [0,255] → get_feat(swapRB=True)")
print("     get_feat swaps RGB→BGR, then: blob = (pixel - 127.5) / 127.5 → correct [-1,+1] range")

# ── 4. Verify get_feat normalisation math ───────────────────────────────────
print("\n[4] Verifying get_feat normalization math...")
# For a pixel value of 200 (uint8 range):
p_base = 200 / 255.0          # after base norm = 0.784
p_raw  = 200.0                 # after raw  norm = 200
# get_feat: blob = (img - 127.5) / 127.5
blob_from_base_pixel = (p_base - 127.5) / 127.5   # ≈ -0.9938
blob_from_raw_pixel  = (p_raw  - 127.5) / 127.5   # ≈  0.569
print(f"   Pixel=200: after 'base' → get_feat sees {p_base:.4f} → blob value = {blob_from_base_pixel:.4f}  (should be ~0.57)")
print(f"   Pixel=200: after 'raw'  → get_feat sees {p_raw:.1f}   → blob value = {blob_from_raw_pixel:.4f}  (correct!)")
print()
# What about the double BGR swap?
print("   Channel swap analysis for 'raw':")
print("     representation.py L173: RGB→BGR  (first swap)")
print("     Buffalo_L.preprocess L78: BGR→RGB (second swap — cancels first!)")
print("     get_feat blobFromImages swapRB=True: RGB→BGR (third swap!)")
print("     NET RESULT: BGR input → BGR output to ONNX")
print("     This is correct IF the model was trained on BGR images (which ArcFace/ONNX expects)")

# ── 5. Run DeepFace.represent() twice with normalization='raw' ───────────────
print("\n" + "=" * 70)
print("[5] Running DeepFace.represent() — normalization='raw' (twice on same image)")
print("=" * 70)

try:
    sys.path.insert(0, '/Users/dinokage/dev/deepface-server/deepface/lib/python3.12/site-packages')
    from deepface import DeepFace

    r1 = DeepFace.represent(
        img_path=test_img_path,
        model_name="Buffalo_L",
        detector_backend="skip",   # skip detection to avoid mtcnn dependency issues
        normalization="raw",
        l2_normalize=False,
        enforce_detection=False,
    )
    e1 = np.array(r1[0]["embedding"])

    r2 = DeepFace.represent(
        img_path=test_img_path,
        model_name="Buffalo_L",
        detector_backend="skip",
        normalization="raw",
        l2_normalize=False,
        enforce_detection=False,
    )
    e2 = np.array(r2[0]["embedding"])

    print(f"\n   Run 1 first 10 values: {e1[:10].tolist()}")
    print(f"   Run 2 first 10 values: {e2[:10].tolist()}")

    # Cosine distance
    def cosine_distance(a, b):
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        cosine_sim = dot / (norm_a * norm_b + 1e-10)
        return 1.0 - cosine_sim

    cos_dist_raw = cosine_distance(e1, e2)
    print(f"\n   Cosine distance (raw, same image x2): {cos_dist_raw:.8f}")
    print(f"   Embedding norm run1: {np.linalg.norm(e1):.4f}")
    print(f"   Embeddings identical: {np.allclose(e1, e2)}")

    # ── 6. Run with normalization='base' ────────────────────────────────────
    print("\n" + "=" * 70)
    print("[6] Running DeepFace.represent() — normalization='base' (twice on same image)")
    print("=" * 70)

    r3 = DeepFace.represent(
        img_path=test_img_path,
        model_name="Buffalo_L",
        detector_backend="skip",
        normalization="base",
        l2_normalize=False,
        enforce_detection=False,
    )
    e3 = np.array(r3[0]["embedding"])

    r4 = DeepFace.represent(
        img_path=test_img_path,
        model_name="Buffalo_L",
        detector_backend="skip",
        normalization="base",
        l2_normalize=False,
        enforce_detection=False,
    )
    e4 = np.array(r4[0]["embedding"])

    print(f"\n   Run 1 first 10 values: {e3[:10].tolist()}")
    print(f"   Run 2 first 10 values: {e4[:10].tolist()}")

    cos_dist_base = cosine_distance(e3, e4)
    print(f"\n   Cosine distance (base, same image x2): {cos_dist_base:.8f}")
    print(f"   Embedding norm run1: {np.linalg.norm(e3):.4f}")
    print(f"   Embeddings identical: {np.allclose(e3, e4)}")

    # ── 7. Cross-normalization comparison ───────────────────────────────────
    print("\n" + "=" * 70)
    print("[7] Cross comparison: raw vs base on same image")
    print("=" * 70)
    cos_raw_vs_base = cosine_distance(e1, e3)
    print(f"   Cosine distance (raw run1 vs base run1): {cos_raw_vs_base:.8f}")

    print("\n   Summary of embedding stats:")
    for name, emb in [("raw ", e1), ("base", e3)]:
        print(f"     {name}: min={emb.min():.4f}  max={emb.max():.4f}  "
              f"mean={emb.mean():.4f}  std={emb.std():.4f}  norm={np.linalg.norm(emb):.4f}")

    # ── 8. Also try a different image to show 'base' gives same embeddings ──
    print("\n" + "=" * 70)
    print("[8] Testing 'base' with a DIFFERENT image to show near-identical embeddings")
    print("=" * 70)
    img2 = np.zeros((224, 224, 3), dtype=np.uint8)
    img2[:] = [100, 100, 200]   # completely different colors
    cv2.ellipse(img2, (112, 112), (80, 100), 0, 0, 360, (255, 200, 100), -1)
    cv2.circle(img2, (70, 90), 15, (20, 20, 80), -1)
    cv2.circle(img2, (154, 90), 15, (20, 20, 80), -1)
    test_img2_path = "/tmp/test_face2.jpg"
    cv2.imwrite(test_img2_path, img2[:, :, ::-1])

    r5 = DeepFace.represent(
        img_path=test_img2_path,
        model_name="Buffalo_L",
        detector_backend="skip",
        normalization="base",
        l2_normalize=False,
        enforce_detection=False,
    )
    e5 = np.array(r5[0]["embedding"])

    cos_diff_base = cosine_distance(e3, e5)
    print(f"   Cosine distance between DIFFERENT faces with 'base': {cos_diff_base:.8f}")
    print(f"   (If near 0.0 → 'base' is producing near-identical garbage embeddings)")

    r6 = DeepFace.represent(
        img_path=test_img2_path,
        model_name="Buffalo_L",
        detector_backend="skip",
        normalization="raw",
        l2_normalize=False,
        enforce_detection=False,
    )
    e6 = np.array(r6[0]["embedding"])
    cos_diff_raw = cosine_distance(e1, e6)
    print(f"   Cosine distance between DIFFERENT faces with 'raw':  {cos_diff_raw:.8f}")
    print(f"   (If > 0.0 → 'raw' correctly differentiates faces)")

except Exception as exc:
    print(f"\n   ERROR running DeepFace: {exc}")
    import traceback
    traceback.print_exc()

# ── 9. Database SQL analysis ─────────────────────────────────────────────────
print("\n" + "=" * 70)
print("[9] DATABASE SQL QUERY ANALYSIS")
print("=" * 70)

print("""
  register() stores with these columns:
    model_name, detector_backend, aligned, l2_normalized, embedding

  INSERT SQL (postgres.py insert_embeddings):
    INSERT INTO embeddings (img_name, face, face_shape, model_name,
        detector_backend, aligned, l2_normalized, embedding,
        face_hash, embedding_hash)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);

  fetch_all_embeddings SQL (postgres.py fetch_all_embeddings):
    SELECT id, img_name, embedding
    FROM embeddings
    WHERE model_name = %s AND detector_backend = %s
      AND aligned = %s AND l2_normalized = %s
    ORDER BY id ASC;

  MISMATCH CHECK:
    register() default args:
      - normalization="base"     ← stored in embedding values, NOT as a column
      - l2_normalize=False       ← stored as l2_normalized column
      - align=True               ← stored as aligned column

    search() default args:
      - normalization="base"     ← must match what was used at register time
      - l2_normalize=False       ← filters WHERE l2_normalized = False
      - align=True               ← filters WHERE aligned = True

  KEY FINDING:
    normalization is NOT stored in the database as a column!
    If you register with normalization="raw" and search with normalization="base"
    (or vice versa), fetch_all_embeddings will RETURN the rows (no normalization
    filter exists in the WHERE clause), but the embedding vectors will be
    incompatible — different normalization → different vector space.
    Distance will be very large → no matches found.

  SCENARIO that causes "same image, no match":
    1. register(..., normalization="raw")   → embedding stored with raw preprocessing
    2. search(...,  normalization="base")   → embedding computed with base preprocessing
       → fetch_all_embeddings returns rows (no normalization filter!)
       → cosine distance between raw embedding and base embedding is large
       → distance > threshold → empty result set

    OR the reverse: register with base, search with raw.
    The normalization mismatch is SILENT — no error is raised.
""")

# ── 10. Root cause summary ───────────────────────────────────────────────────
print("=" * 70)
print("[10] ROOT CAUSE SUMMARY")
print("=" * 70)
print("""
  BUG 1 — normalization="base" produces garbage embeddings for Buffalo_L:
    Pipeline: resize_image → [0,1] float32 → normalize_input(base) → no-op
    Buffalo_L.preprocess: swaps channels (BGR↔RGB) but keeps [0,1] values
    InsightFace get_feat: blobFromImages(mean=127.5, std=127.5) expects [0,255]
    Result: all pixels map to (0~1 - 127.5)/127.5 ≈ -1.0 → near-constant input
    → ONNX model outputs near-identical embeddings for ALL images.

  BUG 2 — normalization="raw" embeddings don't match in database:
    'raw' correctly scales to [0,255] — get_feat produces valid embeddings.
    BUT: normalization is NOT stored as a column in the embeddings table.
    If register() and search() use DIFFERENT normalization settings,
    fetch_all_embeddings has no way to filter by normalization → it returns
    rows registered under a different normalization → vectors are incompatible
    → cosine distance is too large → result is empty.

  BUG 3 — Double channel swap with 'raw' (less critical, but worth noting):
    representation.py L173: RGB→BGR
    Buffalo_L.preprocess L78: BGR→RGB
    get_feat swapRB=True:    RGB→BGR
    Net: 3 swaps = 1 swap. Delivers BGR to ONNX model.
    The model was trained expecting BGR, so this is actually correct.
    But the intermediate double-swap is confusing and error-prone.

  CORRECT FIX:
    Use normalization="raw" for ALL calls to both register() and search().
    Never mix normalization settings between register and search.

    Ideally, store normalization as a column in the embeddings table and
    filter on it in fetch_all_embeddings to prevent silent mismatches.

  RECOMMENDED normalization for Buffalo_L (InsightFace/ArcFace models):
    normalization="raw"   ← correct: gives [0,255] that get_feat expects

    Even better: normalization="ArcFace" would give (pixel-127.5)/128,
    identical to what get_feat does internally, so get_feat would receive
    values in [-1,+1] and then re-normalize them — double normalization,
    still wrong. So "raw" is the correct choice.
""")
