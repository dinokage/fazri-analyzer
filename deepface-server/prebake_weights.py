import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

from deepface import DeepFace

DeepFace.build_model("Buffalo_L", task="facial_recognition")
print("Buffalo_L ready.")

DeepFace.build_model("yolov8n", task="face_detector")
print("yolov8n ready.")

print("Weights baked in.")
