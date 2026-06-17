def analyze_frame(frame):
    from deepface import DeepFace
    result = DeepFace.analyze(
        frame,
        actions=["emotion"],
        enforce_detection=False
    )
    return {
        "dominant_emotion": result[0]["dominant_emotion"],
        "confidence": float(result[0]["emotion"][result[0]["dominant_emotion"]])
    }
