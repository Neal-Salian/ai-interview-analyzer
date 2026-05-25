import whisper
import numpy as np

model = whisper.load_model("base")

def transcribe_chunk(audio_packets: list) -> str:
    audio_array = np.concatenate([
        packet.to_ndarray() for packet in audio_packets
    ]).flatten().astype(np.float32)

    audio_array = audio_array / np.max(np.abs(audio_array))
    result = model.transcribe(audio_array, fp16=False)
    return result["text"].strip()