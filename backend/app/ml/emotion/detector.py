from deepface import DeepFace


def analyze_frame(frame):
    result = DeepFace.analyze(
        frame,
        actions=["emotion"],
        enforce_detection=False
    )
    return {
        "dominant_emotion": result[0]["dominant_emotion"],
        "confidence": result[0]["emotion"][result[0]["dominant_emotion"]]
    }
