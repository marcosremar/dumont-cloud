/**
 * Docker Image and Port Presets
 * Pre-configured options for common use cases
 */

import { PortConfig } from '../types';

// ============================================================================
// Docker Image Presets
// ============================================================================

export interface DockerImagePreset {
  id: string;
  name: string;
  image: string;
  description: string;
  category: 'ml' | 'dev' | 'custom';
  tags?: string[];
  popular?: boolean;
}

export const DOCKER_PRESETS: readonly DockerImagePreset[] = [
  // Machine Learning
  {
    id: 'pytorch-latest',
    name: 'PyTorch (Latest)',
    image: 'pytorch/pytorch:latest',
    description: 'PyTorch com CUDA para deep learning',
    category: 'ml',
    tags: ['ML', 'GPU'],
    popular: true,
  },
  {
    id: 'pytorch-2.1',
    name: 'PyTorch 2.1',
    image: 'pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime',
    description: 'PyTorch 2.1 com CUDA 12.1',
    category: 'ml',
    tags: ['ML', 'GPU', 'Stable'],
  },
  {
    id: 'pytorch-2.0',
    name: 'PyTorch 2.0',
    image: 'pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime',
    description: 'PyTorch 2.0 com CUDA 11.7',
    category: 'ml',
    tags: ['ML', 'GPU'],
  },
  {
    id: 'tensorflow-latest',
    name: 'TensorFlow (Latest)',
    image: 'tensorflow/tensorflow:latest-gpu',
    description: 'TensorFlow com suporte a GPU',
    category: 'ml',
    tags: ['ML', 'GPU'],
    popular: true,
  },
  {
    id: 'tensorflow-2.15',
    name: 'TensorFlow 2.15',
    image: 'tensorflow/tensorflow:2.15.0-gpu',
    description: 'TensorFlow 2.15 com CUDA',
    category: 'ml',
    tags: ['ML', 'GPU', 'Stable'],
  },
  {
    id: 'huggingface',
    name: 'Hugging Face',
    image: 'huggingface/transformers-pytorch-gpu:latest',
    description: 'Transformers + PyTorch para NLP',
    category: 'ml',
    tags: ['ML', 'NLP', 'LLM'],
    popular: true,
  },
  {
    id: 'nvidia-cuda',
    name: 'NVIDIA CUDA Base',
    image: 'nvidia/cuda:12.2.0-runtime-ubuntu22.04',
    description: 'Base CUDA 12.2 para builds customizados',
    category: 'ml',
    tags: ['GPU', 'Base'],
  },
  // Development
  {
    id: 'jupyter-datascience',
    name: 'Jupyter Data Science',
    image: 'jupyter/datascience-notebook:latest',
    description: 'Jupyter com Python, R, Julia',
    category: 'dev',
    tags: ['Jupyter', 'Data Science'],
    popular: true,
  },
  {
    id: 'vscode-server',
    name: 'VS Code Server',
    image: 'codercom/code-server:latest',
    description: 'VS Code no navegador',
    category: 'dev',
    tags: ['IDE', 'Dev'],
  },
  {
    id: 'ubuntu-dev',
    name: 'Ubuntu Dev',
    image: 'ubuntu:22.04',
    description: 'Ubuntu 22.04 limpo para desenvolvimento',
    category: 'dev',
    tags: ['Base', 'Dev'],
  },
  // Custom
  {
    id: 'custom',
    name: 'Imagem Customizada',
    image: '',
    description: 'Digite o nome da sua imagem Docker',
    category: 'custom',
    tags: ['Custom'],
  },
] as const;

// ============================================================================
// Port Presets
// ============================================================================

export interface PortPreset {
  id: string;
  name: string;
  port: string;
  protocol: 'TCP' | 'UDP';
  description: string;
  common?: boolean;
}

export const PORT_PRESETS: readonly PortPreset[] = [
  {
    id: 'ssh',
    name: 'SSH',
    port: '22',
    protocol: 'TCP',
    description: 'Acesso remoto via terminal',
    common: true,
  },
  {
    id: 'jupyter',
    name: 'Jupyter Notebook',
    port: '8888',
    protocol: 'TCP',
    description: 'Interface web do Jupyter',
    common: true,
  },
  {
    id: 'tensorboard',
    name: 'TensorBoard',
    port: '6006',
    protocol: 'TCP',
    description: 'Visualização de métricas de treinamento',
    common: true,
  },
  {
    id: 'http',
    name: 'HTTP',
    port: '80',
    protocol: 'TCP',
    description: 'Servidor web padrão',
  },
  {
    id: 'https',
    name: 'HTTPS',
    port: '443',
    protocol: 'TCP',
    description: 'Servidor web seguro',
  },
  {
    id: 'fastapi',
    name: 'FastAPI/Uvicorn',
    port: '8000',
    protocol: 'TCP',
    description: 'API Python padrão',
  },
  {
    id: 'flask',
    name: 'Flask',
    port: '5000',
    protocol: 'TCP',
    description: 'Servidor Flask padrão',
  },
  {
    id: 'streamlit',
    name: 'Streamlit',
    port: '8501',
    protocol: 'TCP',
    description: 'Apps Streamlit',
  },
  {
    id: 'gradio',
    name: 'Gradio',
    port: '7860',
    protocol: 'TCP',
    description: 'Interface Gradio para ML',
  },
  {
    id: 'vscode',
    name: 'VS Code Server',
    port: '8080',
    protocol: 'TCP',
    description: 'VS Code no navegador',
  },
  {
    id: 'mlflow',
    name: 'MLflow',
    port: '5000',
    protocol: 'TCP',
    description: 'MLflow tracking server',
  },
  {
    id: 'ray-dashboard',
    name: 'Ray Dashboard',
    port: '8265',
    protocol: 'TCP',
    description: 'Ray cluster dashboard',
  },
] as const;

// ============================================================================
// Default Configurations
// ============================================================================

export const DEFAULT_DOCKER_IMAGE = 'pytorch/pytorch:latest';

export const DEFAULT_PORTS: readonly PortConfig[] = [
  { port: '22', protocol: 'TCP' },
  { port: '8888', protocol: 'TCP' },
  { port: '6006', protocol: 'TCP' },
] as const;

// ============================================================================
// Helper Functions
// ============================================================================

export function getDockerPresetById(id: string): DockerImagePreset | undefined {
  return DOCKER_PRESETS.find(p => p.id === id);
}

export function getDockerPresetByImage(image: string): DockerImagePreset | undefined {
  return DOCKER_PRESETS.find(p => p.image === image);
}

export function getPortPresetByPort(port: string): PortPreset | undefined {
  return PORT_PRESETS.find(p => p.port === port);
}

export function getPopularDockerPresets(): DockerImagePreset[] {
  return DOCKER_PRESETS.filter(p => p.popular);
}

export function getCommonPorts(): PortPreset[] {
  return PORT_PRESETS.filter(p => p.common);
}

export function getDockerPresetsByCategory(category: DockerImagePreset['category']): DockerImagePreset[] {
  return DOCKER_PRESETS.filter(p => p.category === category);
}
