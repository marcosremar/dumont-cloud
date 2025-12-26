"""
Whisper Server for Speech-to-Text

Pre-installed in Docker image: dumontcloud/whisper:4.40-cuda12.1
No pip install needed at runtime.

Usage:
    MODEL_ID="openai/whisper-large-v3" PORT=8001 python whisper_server.py
"""

import os
import torch
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import uvicorn

app = FastAPI(title="Whisper Server", version="1.0")

# Load model at startup
MODEL_ID = os.environ.get("MODEL_ID", "openai/whisper-large-v3")
PORT = int(os.environ.get("PORT", 8001))

print(f"Loading model: {MODEL_ID}")
processor = WhisperProcessor.from_pretrained(MODEL_ID)
model = WhisperForConditionalGeneration.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16
)
model.to("cuda")
print("Model loaded!")


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "model": MODEL_ID}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = "en"):
    """
    Transcribe audio file to text.

    Args:
        file: Audio file (wav, mp3, etc)
        language: Target language code (default: en)

    Returns:
        {"text": "transcription..."}
    """
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Load and process audio
        import librosa
        audio, sr = librosa.load(tmp_path, sr=16000)
        inputs = processor(audio, sampling_rate=16000, return_tensors="pt")

        # Convert to float16 to match model dtype
        inputs = {
            k: v.to("cuda").half() if v.dtype == torch.float32 else v.to("cuda")
            for k, v in inputs.items()
        }

        # Generate transcription
        with torch.no_grad():
            generated_ids = model.generate(**inputs, language=language)

        transcription = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        # Cleanup
        os.unlink(tmp_path)

        return {"text": transcription}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/audio/transcriptions")
async def openai_transcribe(file: UploadFile = File(...), language: str = "en"):
    """OpenAI-compatible transcription endpoint"""
    result = await transcribe(file, language)
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
