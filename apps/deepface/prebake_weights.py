"""
Download InsightFace buffalo_l model pack during Docker build.

This runs as a build step (see Dockerfile) so the container starts
without any network fetch. Models are cached in ~/.insightface/models/.
"""
from insightface.app import FaceAnalysis

app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=-1, det_size=(640, 640))
print("buffalo_l (SCRFD + ArcFace) weights baked in.")
