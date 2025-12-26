"""
Video Server for Video Generation

Pre-installed in Docker image: dumontcloud/video:0.28-cuda12.1
Supports: ModelScope, CogVideoX, Zeroscope

Usage:
    MODEL_ID="damo-vilab/text-to-video-ms-1.7b" PORT=8005 python video_server.py
"""

import os
import io
import base64
import tempfile
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from diffusers import DiffusionPipeline
import imageio
import uvicorn

app = FastAPI(title="Video Server", version="1.0")

# Load model at startup
MODEL_ID = os.environ.get("MODEL_ID", "damo-vilab/text-to-video-ms-1.7b")
PORT = int(os.environ.get("PORT", 8005))

print(f"Loading model: {MODEL_ID}")
pipe = DiffusionPipeline.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16
)
pipe.to("cuda")

# Enable memory efficient attention if available
try:
    pipe.enable_model_cpu_offload()
except Exception:
    pass

print("Model loaded!")


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    num_inference_steps: int = 25
    num_frames: int = 16
    guidance_scale: float = 7.5
    fps: int = 8


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "model": MODEL_ID}


@app.post("/generate")
def generate(req: GenerateRequest):
    """
    Generate video from text prompt.

    Returns:
        {"video": "base64_encoded_mp4", "format": "mp4"}
    """
    try:
        # Generate video frames
        video_frames = pipe(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            num_inference_steps=req.num_inference_steps,
            num_frames=req.num_frames,
            guidance_scale=req.guidance_scale,
        ).frames[0]

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            imageio.mimsave(tmp.name, video_frames, fps=req.fps)
            with open(tmp.name, "rb") as f:
                video_bytes = f.read()
            os.unlink(tmp.name)

        video_base64 = base64.b64encode(video_bytes).decode()
        return {"video": video_base64, "format": "mp4"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
