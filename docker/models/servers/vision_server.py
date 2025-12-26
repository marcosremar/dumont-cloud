"""
Vision Server for Image Understanding

Pre-installed in Docker image: dumontcloud/vision:4.40-cuda12.1
Supports: SmolVLM, LLaVA, Qwen2-VL

Usage:
    MODEL_ID="HuggingFaceTB/SmolVLM-256M-Instruct" PORT=8004 python vision_server.py
"""

import os
import io
import base64
import torch
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq
import uvicorn

app = FastAPI(title="Vision Server", version="1.0")

# Load model at startup
MODEL_ID = os.environ.get("MODEL_ID", "HuggingFaceTB/SmolVLM-256M-Instruct")
PORT = int(os.environ.get("PORT", 8004))

print(f"Loading model: {MODEL_ID}")
processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForVision2Seq.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    trust_remote_code=True
)
model.to("cuda")
print("Model loaded!")


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "model": MODEL_ID}


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    prompt: str = Form("Describe this image")
):
    """
    Analyze image with a text prompt.

    Args:
        file: Image file (PNG, JPG, etc)
        prompt: Question or instruction about the image

    Returns:
        {"response": "description..."}
    """
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        prompt_text = processor.apply_chat_template(
            messages,
            add_generation_prompt=True
        )
        inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
        inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=256)

        response = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        return {"response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze_base64")
async def analyze_base64(image_base64: str, prompt: str = "Describe this image"):
    """Analyze base64-encoded image"""
    try:
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        prompt_text = processor.apply_chat_template(
            messages,
            add_generation_prompt=True
        )
        inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
        inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=256)

        response = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        return {"response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
