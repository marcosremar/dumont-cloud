"""
Embeddings Server for Text Embeddings

Pre-installed in Docker image: dumontcloud/embeddings:2.7-cuda12.1
OpenAI-compatible /v1/embeddings endpoint.

Usage:
    MODEL_ID="BAAI/bge-large-en-v1.5" PORT=8003 python embeddings_server.py
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union
from sentence_transformers import SentenceTransformer
import uvicorn

app = FastAPI(title="Embeddings Server", version="1.0")

# Load model at startup
MODEL_ID = os.environ.get("MODEL_ID", "BAAI/bge-large-en-v1.5")
PORT = int(os.environ.get("PORT", 8003))

print(f"Loading model: {MODEL_ID}")
model = SentenceTransformer(MODEL_ID)
model.to("cuda")
print("Model loaded!")


# OpenAI-compatible request/response models
class EmbeddingRequest(BaseModel):
    model: str = ""
    input: Union[str, List[str]]


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: dict


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "model": MODEL_ID}


@app.post("/v1/embeddings", response_model=EmbeddingResponse)
def create_embeddings(req: EmbeddingRequest):
    """
    Create embeddings for text.
    OpenAI-compatible endpoint.

    Args:
        input: Single string or list of strings

    Returns:
        OpenAI-compatible embedding response
    """
    try:
        # Handle both string and list inputs
        texts = [req.input] if isinstance(req.input, str) else req.input

        # Generate embeddings
        embeddings = model.encode(texts, convert_to_numpy=True)

        # Build response
        data = [
            EmbeddingData(embedding=emb.tolist(), index=i)
            for i, emb in enumerate(embeddings)
        ]

        return EmbeddingResponse(
            data=data,
            model=MODEL_ID,
            usage={
                "prompt_tokens": sum(len(t.split()) for t in texts),
                "total_tokens": sum(len(t.split()) for t in texts)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoint for backwards compatibility
class LegacyEmbedRequest(BaseModel):
    texts: List[str]


@app.post("/embed")
def embed(req: LegacyEmbedRequest):
    """Legacy embedding endpoint"""
    embeddings = model.encode(req.texts, convert_to_numpy=True)
    return {"embeddings": embeddings.tolist()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
