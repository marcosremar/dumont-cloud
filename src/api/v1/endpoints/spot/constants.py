"""
Constantes compartilhadas para relatórios Spot.

Especificações de GPU e modelos LLM.
"""

# Especificações de GPU para cálculos
GPU_SPECS = {
    "RTX 4090": {"vram": 24, "tflops": 82.6, "tokens_per_sec": 150, "batch_size": 32},
    "RTX 4080": {"vram": 16, "tflops": 48.7, "tokens_per_sec": 100, "batch_size": 24},
    "RTX 4070 Ti": {"vram": 12, "tflops": 40.1, "tokens_per_sec": 80, "batch_size": 16},
    "RTX 3090": {"vram": 24, "tflops": 35.6, "tokens_per_sec": 120, "batch_size": 32},
    "RTX 3080": {"vram": 10, "tflops": 29.8, "tokens_per_sec": 70, "batch_size": 12},
    "RTX 3080 Ti": {"vram": 12, "tflops": 34.1, "tokens_per_sec": 85, "batch_size": 16},
    "RTX 3070": {"vram": 8, "tflops": 20.3, "tokens_per_sec": 50, "batch_size": 8},
    "A100": {"vram": 80, "tflops": 312, "tokens_per_sec": 400, "batch_size": 128},
    "A100 PCIE": {"vram": 40, "tflops": 156, "tokens_per_sec": 250, "batch_size": 64},
    "H100": {"vram": 80, "tflops": 756, "tokens_per_sec": 600, "batch_size": 128},
    "H100 PCIE": {"vram": 80, "tflops": 378, "tokens_per_sec": 450, "batch_size": 128},
    "A6000": {"vram": 48, "tflops": 38.7, "tokens_per_sec": 180, "batch_size": 48},
    "A40": {"vram": 48, "tflops": 37.4, "tokens_per_sec": 170, "batch_size": 48},
    "RTX 5090": {"vram": 32, "tflops": 104, "tokens_per_sec": 200, "batch_size": 40},
    "RTX 5080": {"vram": 16, "tflops": 56, "tokens_per_sec": 130, "batch_size": 24},
    "L4": {"vram": 24, "tflops": 30.3, "tokens_per_sec": 90, "batch_size": 24},
    "L40": {"vram": 48, "tflops": 90.5, "tokens_per_sec": 200, "batch_size": 48},
    "V100": {"vram": 16, "tflops": 14.1, "tokens_per_sec": 60, "batch_size": 16},
    "RTX A5000": {"vram": 24, "tflops": 27.8, "tokens_per_sec": 95, "batch_size": 24},
    "RTX A4000": {"vram": 16, "tflops": 19.2, "tokens_per_sec": 65, "batch_size": 16},
}

# Modelos LLM recomendados por VRAM
LLM_MODELS = {
    8: ["Llama-2-7B", "Mistral-7B", "Falcon-7B"],
    12: ["Llama-2-7B", "Mistral-7B", "CodeLlama-13B"],
    16: ["Llama-2-13B", "Vicuna-13B", "WizardLM-13B"],
    24: ["Llama-2-13B", "Mixtral-8x7B-q4", "CodeLlama-34B-q4"],
    32: ["Llama-2-70B-q4", "Mixtral-8x7B", "CodeLlama-34B"],
    48: ["Llama-2-70B-q8", "Falcon-40B", "MPT-30B"],
    80: ["Llama-2-70B", "Falcon-180B-q4", "BLOOM-176B-q4"],
}

# Dias da semana
DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
