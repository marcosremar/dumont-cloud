"""
Diffusion Server for Image Generation

Pre-installed in Docker image: dumontcloud/diffusers:0.28-cuda12.1
Supports: SDXL, FLUX, Stable Diffusion

Usage:
    MODEL_ID="stabilityai/stable-diffusion-xl-base-1.0" PORT=8002 python diffusion_server.py
"""

import os
import io
import base64
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from diffusers import DiffusionPipeline
import uvicorn

app = FastAPI(title="Diffusion Server", version="1.0")

# Load model at startup
MODEL_ID = os.environ.get("MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")
PORT = int(os.environ.get("PORT", 8002))

print(f"Loading model: {MODEL_ID}")
pipe = DiffusionPipeline.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16
)
pipe.to("cuda")
print("Model loaded!")


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    width: int = 1024
    height: int = 1024
    seed: int = None


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "model": MODEL_ID}


@app.post("/generate")
def generate(req: GenerateRequest):
    """
    Generate image from text prompt.

    Returns:
        {"image": "base64_encoded_png"}
    """
    try:
        # Set seed for reproducibility
        generator = None
        if req.seed is not None:
            generator = torch.Generator("cuda").manual_seed(req.seed)

        # Generate image
        image = pipe(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            num_inference_steps=req.num_inference_steps,
            guidance_scale=req.guidance_scale,
            width=req.width,
            height=req.height,
            generator=generator,
        ).images[0]

        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return {"image": img_str}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/images/generations")
def openai_generate(req: GenerateRequest):
    """OpenAI-compatible image generation endpoint"""
    result = generate(req)
    return {
        "data": [{"b64_json": result["image"]}]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
