"""
AI Wizard Service - Uses OpenRouter to analyze projects and suggest GPUs
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# GPU knowledge base for the AI
GPU_KNOWLEDGE = """
## GPU Recommendations by Use Case:

### Inferência (Deploy de modelos / APIs):
- RTX 4060/4070, RTX 3060/3070: Modelos pequenos, Stable Diffusion, LLMs até 7B
- Tesla T4: Inferência em produção, custo-eficiente
- A4000, L40: Modelos médios, batch inference

### Treinamento (Fine-tuning / ML Training):
- RTX 4080/4090: Fine-tuning de modelos até 13B, Stable Diffusion training
- RTX 3080/3090: Treinamento de modelos médios
- A5000, A6000: Workloads profissionais, modelos até 30B
- L40S: Alto desempenho para training

### HPC / LLMs (Modelos grandes / Multi-GPU):
- A100 40GB/80GB: LLMs grandes (30B-70B), treinamento distribuído
- H100: Estado da arte, modelos 70B+, máxima performance
- V100: Legacy mas ainda eficiente para muitos workloads

### Requisitos de VRAM por modelo:
- Stable Diffusion XL: 8-12GB
- LLaMA 7B (fp16): 14GB, (int8): 8GB, (int4): 4GB
- LLaMA 13B (fp16): 26GB, (int8): 14GB, (int4): 8GB
- LLaMA 30B (fp16): 60GB, (int8): 32GB, (int4): 16GB
- LLaMA 70B (fp16): 140GB (multi-GPU), (int8): 70GB, (int4): 35GB
- Mixtral 8x7B: 90GB (fp16), 45GB (int8), 24GB (int4)
- FLUX: 24GB+ recomendado
- Whisper Large: 10GB
- GPT-J 6B: 12GB (fp16), 6GB (int8)
"""

SYSTEM_PROMPT = f"""Você é um especialista em GPU Cloud para Machine Learning e IA.
Sua função é analisar o projeto do usuário e recomendar a GPU ideal.

IMPORTANTE: Sempre busque na internet informações atualizadas sobre:
- Requisitos de VRAM do modelo específico mencionado
- Benchmarks de tokens/segundo para o modelo em diferentes GPUs e frameworks
- Performance com diferentes técnicas (quantização INT4/INT8, Flash Attention, etc.)
- Possibilidade de RAM offloading quando VRAM é insuficiente

Use estas informações de referência como base:
{GPU_KNOWLEDGE}

Ao responder, inclua:
1. Informações do modelo (VRAM, quantização recomendada)
2. 3 opções de GPU (mínima, recomendada, máxima)
3. Performance por framework (PyTorch, vLLM, llama.cpp, TGI)
4. RAM offload: quando a VRAM não é suficiente, indicar quanto de RAM do sistema é necessário
5. Técnicas de otimização aplicáveis

GPUs disponíveis e preços médios:
- RTX_3060 (12GB): ~$0.10/hr | RTX_4060 (8GB): ~$0.12/hr
- RTX_4070 (12GB): ~$0.18/hr | RTX_4080 (16GB): ~$0.35/hr
- RTX_3090 (24GB): ~$0.40/hr | RTX_4090 (24GB): ~$0.70/hr
- A6000 (48GB): ~$1.00/hr | L40S (48GB): ~$1.50/hr
- A100 (80GB): ~$2.50/hr | H100 (80GB): ~$4.00/hr

Responda SEMPRE em JSON com este formato:
{{
  "needs_more_info": false,
  "questions": [],
  "recommendation": {{
    "workload_type": "inference|training|hpc",
    "model_info": {{
      "name": "Nome do modelo",
      "parameters": "7B",
      "vram_fp16": "14GB",
      "vram_int8": "8GB",
      "vram_int4": "4GB",
      "recommended_quantization": "INT8 para melhor balanço qualidade/velocidade"
    }},
    "gpu_options": [
      {{
        "tier": "minima",
        "gpu": "RTX_4060",
        "vram": "8GB",
        "price_per_hour": "$0.12",
        "frameworks": {{
          "vllm": "60-80 tok/s (INT4)",
          "pytorch": "30-40 tok/s (INT8)",
          "llama_cpp": "40-60 tok/s (Q4_K_M)"
        }},
        "ram_offload": "Não necessário com INT4/INT8",
        "observation": "Requer quantização, bom para testes"
      }},
      {{
        "tier": "recomendada",
        "gpu": "RTX_4070",
        "vram": "12GB",
        "price_per_hour": "$0.18",
        "frameworks": {{
          "vllm": "100-130 tok/s (INT8)",
          "pytorch": "50-70 tok/s (FP16)",
          "llama_cpp": "70-90 tok/s (Q5_K_M)"
        }},
        "ram_offload": "Não necessário",
        "observation": "Melhor custo-benefício"
      }},
      {{
        "tier": "maxima",
        "gpu": "RTX_4090",
        "vram": "24GB",
        "price_per_hour": "$0.70",
        "frameworks": {{
          "vllm": "180-220 tok/s (FP16)",
          "pytorch": "100-130 tok/s (FP16)",
          "tgi": "150-180 tok/s (FP16)"
        }},
        "ram_offload": "Não necessário",
        "observation": "Máxima performance, FP16 sem quantização"
      }}
    ],
    "optimization_tips": [
      "Use Flash Attention 2 para reduzir uso de VRAM",
      "vLLM oferece melhor throughput para serving",
      "INT8 oferece ~95% da qualidade com metade da VRAM"
    ],
    "explanation": "Explicação detalhada baseada nos benchmarks...",
    "search_sources": "Fontes: HuggingFace, vLLM benchmarks, etc."
  }}
}}

Se precisar de mais informações:
{{
  "needs_more_info": true,
  "questions": ["Qual modelo específico?", "Qual framework pretende usar?"],
  "recommendation": null
}}
"""


class AIWizardService:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "openai/gpt-4o-mini-search-preview"  # Modelo com busca na web

    async def analyze_project(
        self,
        project_description: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a project description and return GPU recommendations
        """
        if not self.api_key:
            logger.warning("OpenRouter API key not configured")
            return self._fallback_recommendation(project_description, conversation_history)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history if exists
        if conversation_history:
            messages.extend(conversation_history)

        # Add current message
        messages.append({"role": "user", "content": project_description})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://dumontcloud.com",
                        "X-Title": "Dumont Cloud GPU Wizard"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 1000,
                        "response_format": {"type": "json_object"}
                    }
                )

                if response.status_code != 200:
                    logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                    return self._fallback_recommendation(project_description, conversation_history)

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Parse JSON response
                import json
                try:
                    result = json.loads(content)
                    return {
                        "success": True,
                        "data": result,
                        "model_used": self.model
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse AI response: {content}")
                    return self._fallback_recommendation(project_description, conversation_history)

        except Exception as e:
            logger.error(f"AI Wizard error: {e}")
            return self._fallback_recommendation(project_description, conversation_history)

    def _fallback_recommendation(self, description: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Fallback recommendation when AI is not available.
        Analyzes the full conversation context.
        """
        # Combine current description with conversation history
        full_context = description.lower()
        if conversation_history:
            for msg in conversation_history:
                if msg.get("content"):
                    full_context += " " + msg["content"].lower()

        # Detect workload type
        is_inference = any(word in full_context for word in [
            "inferencia", "inferência", "inference", "deploy", "api", "serving",
            "rodar", "executar", "vllm", "tgi", "ollama"
        ])
        is_training = any(word in full_context for word in [
            "training", "treinamento", "fine-tune", "finetune", "fine tuning", "fine-tuning",
            "treinar", "train", "lora", "qlora", "finetuning"
        ])

        # Detect model size
        has_tiny_model = any(word in full_context for word in [
            "0.5b", "0,5b", "0.5 b", "1b", "1.5b", "2b", "3b", "tiny", "small", "mini",
            "qwen 2.5", "qwen2.5", "qwen-2.5", "phi-3", "phi3", "tinyllama"
        ])
        has_small_model = any(word in full_context for word in [
            "7b", "8b", "qwen", "phi", "gemma", "mistral 7b"
        ]) and not has_tiny_model
        has_medium_model = any(word in full_context for word in [
            "13b", "14b", "llama 13", "codellama"
        ])
        has_large_model = any(word in full_context for word in [
            "30b", "33b", "34b", "llama 30", "deepseek 33"
        ])
        has_huge_model = any(word in full_context for word in [
            "70b", "65b", "mixtral", "llama 70", "falcon 180", "distributed", "multi-gpu"
        ])

        # Detect image generation
        is_image_gen = any(word in full_context for word in [
            "stable diffusion", "sdxl", "flux", "comfyui", "automatic1111",
            "imagem", "image", "diffusion", "midjourney"
        ])

        # HPC / Huge models
        if has_huge_model:
            return {
                "success": True,
                "data": {
                    "needs_more_info": False,
                    "questions": [],
                    "recommendation": {
                        "workload_type": "hpc",
                        "min_vram_gb": 80,
                        "recommended_gpus": ["H100", "A100_80GB", "A100"],
                        "explanation": "Para modelos grandes como LLaMA 70B ou Mixtral, você precisa de GPUs de datacenter com alta VRAM.",
                        "tier_suggestion": "Ultra"
                    }
                },
                "model_used": "fallback"
            }

        # Large models (30B+)
        if has_large_model:
            return {
                "success": True,
                "data": {
                    "needs_more_info": False,
                    "questions": [],
                    "recommendation": {
                        "workload_type": "training" if is_training else "inference",
                        "min_vram_gb": 48,
                        "recommended_gpus": ["A100", "A6000", "L40S"],
                        "explanation": "Para modelos de 30B+ parâmetros, você precisa de GPUs profissionais com 48GB+ de VRAM.",
                        "tier_suggestion": "Ultra"
                    }
                },
                "model_used": "fallback"
            }

        # Medium models (13B)
        if has_medium_model:
            vram = 24 if is_inference else 32
            return {
                "success": True,
                "data": {
                    "needs_more_info": False,
                    "questions": [],
                    "recommendation": {
                        "workload_type": "training" if is_training else "inference",
                        "min_vram_gb": vram,
                        "recommended_gpus": ["RTX_4090", "A6000", "RTX_3090"],
                        "explanation": f"Para modelos de 13B, recomendo GPUs com {vram}GB+ de VRAM. RTX 4090 oferece excelente custo-benefício.",
                        "tier_suggestion": "Rapido"
                    }
                },
                "model_used": "fallback"
            }

        # Small models (7B-8B)
        if has_small_model:
            workload = "training" if is_training else "inference"
            if is_training:
                return {
                    "success": True,
                    "data": {
                        "needs_more_info": False,
                        "questions": [],
                        "recommendation": {
                            "workload_type": workload,
                            "model_info": {
                                "name": "Modelo 7B-8B (Training)",
                                "parameters": "7B-8B",
                                "vram_fp16": "14-16GB",
                                "vram_int8": "8-10GB",
                                "vram_int4": "4-5GB",
                                "recommended_quantization": "QLoRA (INT4) para fine-tuning eficiente"
                            },
                            "gpu_options": [
                                {
                                    "tier": "minima",
                                    "gpu": "RTX_3090",
                                    "vram": "24GB",
                                    "price_per_hour": "$0.40",
                                    "frameworks": {
                                        "pytorch": "LoRA: ~500 samples/hr",
                                        "transformers": "QLoRA: ~800 samples/hr"
                                    },
                                    "ram_offload": "16GB RAM para gradient offload",
                                    "observation": "Funciona bem com QLoRA, custo menor"
                                },
                                {
                                    "tier": "recomendada",
                                    "gpu": "RTX_4090",
                                    "vram": "24GB",
                                    "price_per_hour": "$0.70",
                                    "frameworks": {
                                        "pytorch": "LoRA: ~1000 samples/hr",
                                        "transformers": "QLoRA: ~1500 samples/hr"
                                    },
                                    "ram_offload": "Não necessário com QLoRA",
                                    "observation": "Melhor custo-benefício, Ada Lovelace otimizada"
                                },
                                {
                                    "tier": "maxima",
                                    "gpu": "A6000",
                                    "vram": "48GB",
                                    "price_per_hour": "$1.00",
                                    "frameworks": {
                                        "pytorch": "Full fine-tune: ~600 samples/hr",
                                        "transformers": "LoRA FP16: ~1200 samples/hr"
                                    },
                                    "ram_offload": "Não necessário",
                                    "observation": "Full fine-tuning possível, ECC para estabilidade"
                                }
                            ],
                            "optimization_tips": [
                                "Use QLoRA para fine-tuning com 8GB VRAM disponível",
                                "Gradient checkpointing reduz uso de VRAM em 30-40%",
                                "DeepSpeed ZeRO-2 para modelos que não cabem na VRAM",
                                "bitsandbytes para quantização durante training"
                            ],
                            "explanation": "Para fine-tuning de modelos 7B-8B, recomendo RTX 4090 com QLoRA. Com 24GB é possível fazer LoRA em FP16 ou full fine-tune com gradient checkpointing.",
                            "search_sources": "Estimativas baseadas em benchmarks de HuggingFace (fallback)"
                        }
                    },
                    "model_used": "fallback"
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "needs_more_info": False,
                        "questions": [],
                        "recommendation": {
                            "workload_type": workload,
                            "model_info": {
                                "name": "Modelo 7B-8B (Inference)",
                                "parameters": "7B-8B",
                                "vram_fp16": "14-16GB",
                                "vram_int8": "8-10GB",
                                "vram_int4": "4-5GB",
                                "recommended_quantization": "INT8 para melhor balanço qualidade/velocidade"
                            },
                            "gpu_options": [
                                {
                                    "tier": "minima",
                                    "gpu": "RTX_4060",
                                    "vram": "8GB",
                                    "price_per_hour": "$0.12",
                                    "frameworks": {
                                        "vllm": "25-35 tok/s (INT4/AWQ)",
                                        "pytorch": "15-20 tok/s (INT4)",
                                        "llama_cpp": "20-30 tok/s (Q4_K_M)"
                                    },
                                    "ram_offload": "8GB RAM para camadas extras (Q4)",
                                    "observation": "Requer INT4, bom para testes e dev"
                                },
                                {
                                    "tier": "recomendada",
                                    "gpu": "RTX_4080",
                                    "vram": "16GB",
                                    "price_per_hour": "$0.35",
                                    "frameworks": {
                                        "vllm": "60-80 tok/s (INT8/GPTQ)",
                                        "pytorch": "35-50 tok/s (INT8)",
                                        "llama_cpp": "50-70 tok/s (Q8_0)"
                                    },
                                    "ram_offload": "Não necessário com INT8",
                                    "observation": "Melhor custo-benefício para produção"
                                },
                                {
                                    "tier": "maxima",
                                    "gpu": "RTX_4090",
                                    "vram": "24GB",
                                    "price_per_hour": "$0.70",
                                    "frameworks": {
                                        "vllm": "100-130 tok/s (FP16)",
                                        "pytorch": "60-80 tok/s (FP16)",
                                        "tgi": "90-110 tok/s (FP16)"
                                    },
                                    "ram_offload": "Não necessário",
                                    "observation": "FP16 completo, máxima qualidade"
                                }
                            ],
                            "optimization_tips": [
                                "vLLM com PagedAttention para melhor throughput",
                                "AWQ/GPTQ para quantização com qualidade preservada",
                                "Flash Attention 2 reduz latência em 40%",
                                "Continuous batching para múltiplos usuários"
                            ],
                            "explanation": "Para inferência de modelos 7B-8B, RTX 4080 oferece bom custo-benefício com INT8. RTX 4090 permite FP16 completo sem quantização.",
                            "search_sources": "Estimativas baseadas em benchmarks vLLM/llama.cpp (fallback)"
                        }
                    },
                    "model_used": "fallback"
                }

        # Tiny models (0.5B-3B)
        if has_tiny_model:
            return {
                "success": True,
                "data": {
                    "needs_more_info": False,
                    "questions": [],
                    "recommendation": {
                        "workload_type": "training" if is_training else "inference",
                        "model_info": {
                            "name": "Modelo pequeno (0.5B-3B)",
                            "parameters": "0.5B-3B",
                            "vram_fp16": "2-6GB",
                            "vram_int8": "1-3GB",
                            "vram_int4": "0.5-2GB",
                            "recommended_quantization": "FP16 recomendado - modelo pequeno não precisa quantização"
                        },
                        "gpu_options": [
                            {
                                "tier": "minima",
                                "gpu": "RTX_3060",
                                "vram": "12GB",
                                "price_per_hour": "$0.10",
                                "frameworks": {
                                    "vllm": "200-300 tok/s (FP16)",
                                    "pytorch": "100-150 tok/s (FP16)",
                                    "llama_cpp": "150-250 tok/s (F16)"
                                },
                                "ram_offload": "Não necessário",
                                "observation": "Mais econômica, boa para testes e desenvolvimento"
                            },
                            {
                                "tier": "recomendada",
                                "gpu": "RTX_4060",
                                "vram": "8GB",
                                "price_per_hour": "$0.12",
                                "frameworks": {
                                    "vllm": "300-400 tok/s (FP16)",
                                    "pytorch": "150-200 tok/s (FP16)",
                                    "llama_cpp": "250-350 tok/s (F16)"
                                },
                                "ram_offload": "Não necessário",
                                "observation": "Melhor custo-benefício, Ada Lovelace mais eficiente"
                            },
                            {
                                "tier": "maxima",
                                "gpu": "RTX_4070",
                                "vram": "12GB",
                                "price_per_hour": "$0.18",
                                "frameworks": {
                                    "vllm": "400-550 tok/s (FP16)",
                                    "pytorch": "200-280 tok/s (FP16)",
                                    "llama_cpp": "350-450 tok/s (F16)"
                                },
                                "ram_offload": "Não necessário",
                                "observation": "Máxima performance para este modelo"
                            }
                        ],
                        "optimization_tips": [
                            "Modelo pequeno - não precisa de quantização, use FP16",
                            "vLLM oferece melhor throughput para serving em produção",
                            "llama.cpp é eficiente para uso local e baixa latência",
                            "Flash Attention 2 pode acelerar ainda mais"
                        ],
                        "explanation": "Para modelos pequenos (0.5B-3B), GPUs básicas são suficientes. Modelos dessa escala rodam muito rápido mesmo em hardware modesto. Use FP16 completo já que o modelo cabe facilmente na VRAM.",
                        "search_sources": "Estimativas baseadas em benchmarks gerais de LLMs (fallback)"
                    }
                },
                "model_used": "fallback"
            }

        # Image generation
        if is_image_gen:
            return {
                "success": True,
                "data": {
                    "needs_more_info": False,
                    "questions": [],
                    "recommendation": {
                        "workload_type": "inference",
                        "min_vram_gb": 12,
                        "recommended_gpus": ["RTX_4070_Ti", "RTX_4080", "RTX_3090"],
                        "explanation": "Para geração de imagens com Stable Diffusion ou FLUX, 12-24GB de VRAM é ideal.",
                        "tier_suggestion": "Medio"
                    }
                },
                "model_used": "fallback"
            }

        # Training without specific model
        if is_training:
            return {
                "success": True,
                "data": {
                    "needs_more_info": False,
                    "questions": [],
                    "recommendation": {
                        "workload_type": "training",
                        "min_vram_gb": 24,
                        "recommended_gpus": ["RTX_4090", "A6000", "RTX_3090"],
                        "explanation": "Para treinamento e fine-tuning, GPUs com alta VRAM e boa performance de compute são ideais.",
                        "tier_suggestion": "Rapido"
                    }
                },
                "model_used": "fallback"
            }

        # Inference without specific model
        if is_inference:
            return {
                "success": True,
                "data": {
                    "needs_more_info": False,
                    "questions": [],
                    "recommendation": {
                        "workload_type": "inference",
                        "min_vram_gb": 12,
                        "recommended_gpus": ["RTX_4070", "RTX_4080", "Tesla_T4"],
                        "explanation": "Para inferência de modelos, GPUs de médio porte oferecem bom custo-benefício.",
                        "tier_suggestion": "Medio"
                    }
                },
                "model_used": "fallback"
            }

        # Default: ask for more info
        return {
            "success": True,
            "data": {
                "needs_more_info": True,
                "questions": [
                    "Qual modelo você pretende usar? (ex: LLaMA 7B, Qwen 2.5, Stable Diffusion)",
                    "É para inferência (rodar modelo) ou treinamento/fine-tuning?"
                ],
                "recommendation": None
            },
            "model_used": "fallback"
        }


# Singleton instance
ai_wizard_service = AIWizardService()
