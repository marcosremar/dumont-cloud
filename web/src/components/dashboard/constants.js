// Dashboard Constants - GPU Options, Categories, Regions, etc.

export const GPU_OPTIONS = [
  { value: 'any', label: 'Any GPU' },
  // Consumer
  { value: 'RTX_3060', label: 'RTX 3060' },
  { value: 'RTX_3060_Ti', label: 'RTX 3060 Ti' },
  { value: 'RTX_3070', label: 'RTX 3070' },
  { value: 'RTX_3070_Ti', label: 'RTX 3070 Ti' },
  { value: 'RTX_3080', label: 'RTX 3080' },
  { value: 'RTX_3080_Ti', label: 'RTX 3080 Ti' },
  { value: 'RTX_3090', label: 'RTX 3090' },
  { value: 'RTX_3090_Ti', label: 'RTX 3090 Ti' },
  { value: 'RTX_4060', label: 'RTX 4060' },
  { value: 'RTX_4060_Ti', label: 'RTX 4060 Ti' },
  { value: 'RTX_4070', label: 'RTX 4070' },
  { value: 'RTX_4070_Ti', label: 'RTX 4070 Ti' },
  { value: 'RTX_4070_Ti_Super', label: 'RTX 4070 Ti Super' },
  { value: 'RTX_4080', label: 'RTX 4080' },
  { value: 'RTX_4080_Super', label: 'RTX 4080 Super' },
  { value: 'RTX_4090', label: 'RTX 4090' },
  { value: 'RTX_5090', label: 'RTX 5090' },
  // Datacenter
  { value: 'A100', label: 'A100' },
  { value: 'A100_PCIE', label: 'A100 PCIe' },
  { value: 'A100_SXM4', label: 'A100 SXM4' },
  { value: 'A100_80GB', label: 'A100 80GB' },
  { value: 'H100', label: 'H100' },
  { value: 'H100_PCIe', label: 'H100 PCIe' },
  { value: 'H100_SXM5', label: 'H100 SXM5' },
  { value: 'A6000', label: 'RTX A6000' },
  { value: 'A5000', label: 'RTX A5000' },
  { value: 'A4000', label: 'RTX A4000' },
  { value: 'A4500', label: 'RTX A4500' },
  { value: 'L40', label: 'L40' },
  { value: 'L40S', label: 'L40S' },
  { value: 'V100', label: 'V100' },
  { value: 'V100_SXM2', label: 'V100 SXM2' },
  { value: 'Tesla_T4', label: 'Tesla T4' },
  { value: 'P100', label: 'P100' },
];

export const GPU_CATEGORIES = [
  {
    id: 'any',
    name: 'Automatic',
    icon: 'auto',
    description: 'Best value',
    gpus: []
  },
  {
    id: 'inference',
    name: 'Inference',
    icon: 'inference',
    description: 'Model deployment / APIs',
    gpus: ['RTX_4060', 'RTX_4060_Ti', 'RTX_4070', 'RTX_3060', 'RTX_3060_Ti', 'RTX_3070', 'RTX_3070_Ti', 'Tesla_T4', 'A4000', 'L40']
  },
  {
    id: 'training',
    name: 'Training',
    icon: 'training',
    description: 'Fine-tuning / ML Training',
    gpus: ['RTX_4080', 'RTX_4080_Super', 'RTX_4090', 'RTX_3080', 'RTX_3080_Ti', 'RTX_3090', 'RTX_3090_Ti', 'RTX_5090', 'A5000', 'A6000', 'L40S']
  },
  {
    id: 'hpc',
    name: 'HPC / LLMs',
    icon: 'hpc',
    description: 'Large models / Multi-GPU',
    gpus: ['A100', 'A100_PCIE', 'A100_SXM4', 'A100_80GB', 'H100', 'H100_PCIe', 'H100_SXM5', 'V100', 'V100_SXM2']
  },
];

export const REGION_OPTIONS = [
  { value: 'any', label: 'All Regions' },
  { value: 'US', label: 'United States' },
  { value: 'EU', label: 'Europe' },
  { value: 'ASIA', label: 'Asia' },
  { value: 'SA', label: 'South America' },
  { value: 'OC', label: 'Oceania' },
  { value: 'AF', label: 'Africa' },
];

export const CUDA_OPTIONS = [
  { value: 'any', label: 'Any version' },
  { value: '11.0', label: 'CUDA 11.0+' },
  { value: '11.7', label: 'CUDA 11.7+' },
  { value: '11.8', label: 'CUDA 11.8+' },
  { value: '12.0', label: 'CUDA 12.0+' },
  { value: '12.1', label: 'CUDA 12.1+' },
  { value: '12.2', label: 'CUDA 12.2+' },
  { value: '12.4', label: 'CUDA 12.4+' },
];

export const ORDER_OPTIONS = [
  { value: 'dph_total', label: 'Price (lowest first)' },
  { value: 'dlperf', label: 'DL Performance (highest)' },
  { value: 'gpu_ram', label: 'GPU RAM (highest)' },
  { value: 'inet_down', label: 'Download (highest)' },
  { value: 'reliability', label: 'Reliability' },
  { value: 'pcie_bw', label: 'PCIe Bandwidth' },
];

export const RENTAL_TYPE_OPTIONS = [
  { value: 'on-demand', label: 'On-Demand' },
  { value: 'bid', label: 'Bid/Interruptible' },
];

export const PERFORMANCE_TIERS = [
  {
    name: 'CPU',
    level: 0,
    color: 'blue',
    speed: '100-500 Mbps',
    time: '~1 min',
    gpu: 'No GPU',
    vram: 'N/A',
    priceRange: '$0.01 - $0.05/hr',
    description: 'CPU only. For tasks that don\'t need GPU.',
    filter: { max_price: 0.10, cpu_only: true }
  },
  {
    name: 'Slow',
    level: 1,
    color: 'slate',
    speed: '100-250 Mbps',
    time: '~5 min',
    gpu: 'RTX 3070/3080',
    vram: '8-12GB VRAM',
    priceRange: '$0.05 - $0.25/hr',
    description: 'Budget-friendly. Ideal for basic tasks and testing.',
    filter: { max_price: 0.25, min_gpu_ram: 8 }
  },
  {
    name: 'Medium',
    level: 2,
    color: 'amber',
    speed: '500-1000 Mbps',
    time: '~2 min',
    gpu: 'RTX 4070/4080',
    vram: '12-16GB VRAM',
    priceRange: '$0.25 - $0.50/hr',
    description: 'Balanced. Good for daily development.',
    filter: { max_price: 0.50, min_gpu_ram: 12 }
  },
  {
    name: 'Fast',
    level: 3,
    color: 'lime',
    speed: '1000-2000 Mbps',
    time: '~30s',
    gpu: 'RTX 4090',
    vram: '24GB VRAM',
    priceRange: '$0.50 - $1.00/hr',
    description: 'High performance. Training and heavy workloads.',
    filter: { max_price: 1.00, min_gpu_ram: 24 }
  },
  {
    name: 'Ultra',
    level: 4,
    color: 'green',
    speed: '2000+ Mbps',
    time: '~10s',
    gpu: 'A100/H100',
    vram: '40-80GB VRAM',
    priceRange: '$1.00 - $10.00/hr',
    description: 'Maximum power. For the most demanding tasks.',
    filter: { max_price: 10.0, min_gpu_ram: 40 }
  }
];

export const COUNTRY_DATA = {
  // Regions (select multiple countries)
  'usa': { codes: ['US', 'CA', 'MX'], name: 'USA', isRegion: true },
  'europe': { codes: ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'], name: 'Europe', isRegion: true },
  'asia': { codes: ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW'], name: 'Asia', isRegion: true },
  'south america': { codes: ['BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'], name: 'South America', isRegion: true },

  // Individual countries (multiple search keys for same country)
  'united states': { codes: ['US'], name: 'United States', isRegion: false },
  'usa': { codes: ['US'], name: 'United States', isRegion: false },
  'estados unidos': { codes: ['US'], name: 'United States', isRegion: false },
  'canada': { codes: ['CA'], name: 'Canada', isRegion: false },
  'canadá': { codes: ['CA'], name: 'Canada', isRegion: false },
  'mexico': { codes: ['MX'], name: 'Mexico', isRegion: false },
  'méxico': { codes: ['MX'], name: 'Mexico', isRegion: false },
  'brazil': { codes: ['BR'], name: 'Brazil', isRegion: false },
  'brasil': { codes: ['BR'], name: 'Brazil', isRegion: false },
  'argentina': { codes: ['AR'], name: 'Argentina', isRegion: false },
  'chile': { codes: ['CL'], name: 'Chile', isRegion: false },
  'colombia': { codes: ['CO'], name: 'Colombia', isRegion: false },
  'colômbia': { codes: ['CO'], name: 'Colombia', isRegion: false },
  'united kingdom': { codes: ['GB'], name: 'United Kingdom', isRegion: false },
  'uk': { codes: ['GB'], name: 'United Kingdom', isRegion: false },
  'reino unido': { codes: ['GB'], name: 'United Kingdom', isRegion: false },
  'england': { codes: ['GB'], name: 'United Kingdom', isRegion: false },
  'inglaterra': { codes: ['GB'], name: 'United Kingdom', isRegion: false },
  'france': { codes: ['FR'], name: 'France', isRegion: false },
  'frança': { codes: ['FR'], name: 'France', isRegion: false },
  'germany': { codes: ['DE'], name: 'Germany', isRegion: false },
  'alemanha': { codes: ['DE'], name: 'Germany', isRegion: false },
  'spain': { codes: ['ES'], name: 'Spain', isRegion: false },
  'espanha': { codes: ['ES'], name: 'Spain', isRegion: false },
  'italy': { codes: ['IT'], name: 'Italy', isRegion: false },
  'itália': { codes: ['IT'], name: 'Italy', isRegion: false },
  'italia': { codes: ['IT'], name: 'Italy', isRegion: false },
  'portugal': { codes: ['PT'], name: 'Portugal', isRegion: false },
  'japan': { codes: ['JP'], name: 'Japan', isRegion: false },
  'japão': { codes: ['JP'], name: 'Japan', isRegion: false },
  'japao': { codes: ['JP'], name: 'Japan', isRegion: false },
  'china': { codes: ['CN'], name: 'China', isRegion: false },
  'south korea': { codes: ['KR'], name: 'South Korea', isRegion: false },
  'coreia do sul': { codes: ['KR'], name: 'South Korea', isRegion: false },
  'korea': { codes: ['KR'], name: 'South Korea', isRegion: false },
  'singapore': { codes: ['SG'], name: 'Singapore', isRegion: false },
  'singapura': { codes: ['SG'], name: 'Singapore', isRegion: false },
  'india': { codes: ['IN'], name: 'India', isRegion: false },
  'índia': { codes: ['IN'], name: 'India', isRegion: false },
};

export const COUNTRY_NAMES = {
  'US': 'United States', 'CA': 'Canada', 'MX': 'Mexico',
  'GB': 'United Kingdom', 'FR': 'France', 'DE': 'Germany', 'ES': 'Spain', 'IT': 'Italy', 'PT': 'Portugal',
  'JP': 'Japan', 'CN': 'China', 'KR': 'South Korea', 'SG': 'Singapore', 'IN': 'India',
  'BR': 'Brazil', 'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia',
};

export const DEMO_OFFERS = [
  // ==================== CPU-ONLY TIER (< $0.10) ====================
  // 6 offers (2 per major region: US, EU, ASIA)
  { id: 2001, gpu_name: 'CPU Only', num_gpus: 0, gpu_ram: 0, cpu_cores: 4, cpu_ram: 16, disk_space: 50, dph_total: 0.02, inet_down: 200, verified: true, geolocation: 'US', isCPU: true },
  { id: 2002, gpu_name: 'CPU Only', num_gpus: 0, gpu_ram: 0, cpu_cores: 8, cpu_ram: 32, disk_space: 100, dph_total: 0.04, inet_down: 300, verified: true, geolocation: 'EU', isCPU: true },
  { id: 2003, gpu_name: 'CPU Only', num_gpus: 0, gpu_ram: 0, cpu_cores: 4, cpu_ram: 16, disk_space: 50, dph_total: 0.03, inet_down: 250, verified: true, geolocation: 'EU', isCPU: true },
  { id: 2004, gpu_name: 'CPU Only', num_gpus: 0, gpu_ram: 0, cpu_cores: 8, cpu_ram: 32, disk_space: 100, dph_total: 0.05, inet_down: 350, verified: true, geolocation: 'US', isCPU: true },
  { id: 2005, gpu_name: 'CPU Only', num_gpus: 0, gpu_ram: 0, cpu_cores: 6, cpu_ram: 24, disk_space: 80, dph_total: 0.04, inet_down: 300, verified: true, geolocation: 'ASIA', isCPU: true },
  { id: 2006, gpu_name: 'CPU Only', num_gpus: 0, gpu_ram: 0, cpu_cores: 12, cpu_ram: 48, disk_space: 150, dph_total: 0.08, inet_down: 400, verified: true, geolocation: 'ASIA', isCPU: true },

  // ==================== TIER SLOW (< $0.25) - min_gpu_ram: 8 ====================
  // 9 offers (3 US, 3 EU, 3 ASIA)
  { id: 1001, gpu_name: 'RTX 3060', num_gpus: 1, gpu_ram: 12, cpu_cores: 8, cpu_ram: 32, disk_space: 100, dph_total: 0.08, inet_down: 500, verified: true, geolocation: 'EU' },
  { id: 1002, gpu_name: 'RTX 3060', num_gpus: 1, gpu_ram: 12, cpu_cores: 6, cpu_ram: 24, disk_space: 80, dph_total: 0.10, inet_down: 400, verified: false, geolocation: 'US' },
  { id: 1003, gpu_name: 'RTX 3060 Ti', num_gpus: 1, gpu_ram: 8, cpu_cores: 8, cpu_ram: 32, disk_space: 100, dph_total: 0.12, inet_down: 500, verified: true, geolocation: 'US' },
  { id: 1004, gpu_name: 'RTX 4060', num_gpus: 1, gpu_ram: 8, cpu_cores: 8, cpu_ram: 32, disk_space: 100, dph_total: 0.12, inet_down: 600, verified: true, geolocation: 'EU' },
  { id: 1005, gpu_name: 'RTX 3070', num_gpus: 1, gpu_ram: 8, cpu_cores: 8, cpu_ram: 32, disk_space: 120, dph_total: 0.15, inet_down: 600, verified: true, geolocation: 'EU' },
  { id: 1014, gpu_name: 'RTX 3070', num_gpus: 1, gpu_ram: 8, cpu_cores: 10, cpu_ram: 48, disk_space: 150, dph_total: 0.18, inet_down: 700, verified: true, geolocation: 'US' },
  { id: 1025, gpu_name: 'RTX 3060', num_gpus: 1, gpu_ram: 12, cpu_cores: 8, cpu_ram: 32, disk_space: 100, dph_total: 0.09, inet_down: 450, verified: true, geolocation: 'ASIA' },
  { id: 1026, gpu_name: 'RTX 3070', num_gpus: 1, gpu_ram: 8, cpu_cores: 8, cpu_ram: 32, disk_space: 100, dph_total: 0.14, inet_down: 550, verified: true, geolocation: 'ASIA' },
  { id: 1027, gpu_name: 'RTX 4060', num_gpus: 1, gpu_ram: 8, cpu_cores: 10, cpu_ram: 48, disk_space: 120, dph_total: 0.16, inet_down: 600, verified: true, geolocation: 'ASIA' },

  // ==================== TIER MEDIUM ($0.25-$0.50) - min_gpu_ram: 12 ====================
  // 9 offers (3 US, 3 EU, 3 ASIA)
  { id: 1006, gpu_name: 'RTX 4070', num_gpus: 1, gpu_ram: 12, cpu_cores: 12, cpu_ram: 48, disk_space: 150, dph_total: 0.28, inet_down: 800, verified: true, geolocation: 'EU' },
  { id: 1015, gpu_name: 'RTX 4070 Ti', num_gpus: 1, gpu_ram: 12, cpu_cores: 10, cpu_ram: 48, disk_space: 150, dph_total: 0.30, inet_down: 850, verified: true, geolocation: 'US' },
  { id: 1007, gpu_name: 'RTX 4080', num_gpus: 1, gpu_ram: 16, cpu_cores: 12, cpu_ram: 48, disk_space: 150, dph_total: 0.35, inet_down: 800, verified: true, geolocation: 'EU' },
  { id: 1016, gpu_name: 'RTX 3090', num_gpus: 1, gpu_ram: 24, cpu_cores: 14, cpu_ram: 64, disk_space: 200, dph_total: 0.38, inet_down: 900, verified: true, geolocation: 'US' },
  { id: 1008, gpu_name: 'RTX 3090', num_gpus: 1, gpu_ram: 24, cpu_cores: 12, cpu_ram: 64, disk_space: 200, dph_total: 0.40, inet_down: 800, verified: true, geolocation: 'US' },
  { id: 1017, gpu_name: 'RTX 4080', num_gpus: 1, gpu_ram: 16, cpu_cores: 16, cpu_ram: 64, disk_space: 200, dph_total: 0.45, inet_down: 1000, verified: true, geolocation: 'EU' },
  { id: 1028, gpu_name: 'RTX 4070', num_gpus: 1, gpu_ram: 12, cpu_cores: 10, cpu_ram: 48, disk_space: 150, dph_total: 0.26, inet_down: 750, verified: true, geolocation: 'ASIA' },
  { id: 1029, gpu_name: 'RTX 3090', num_gpus: 1, gpu_ram: 24, cpu_cores: 12, cpu_ram: 64, disk_space: 180, dph_total: 0.35, inet_down: 850, verified: true, geolocation: 'ASIA' },
  { id: 1030, gpu_name: 'RTX 4080', num_gpus: 1, gpu_ram: 16, cpu_cores: 14, cpu_ram: 64, disk_space: 200, dph_total: 0.42, inet_down: 900, verified: true, geolocation: 'ASIA' },

  // ==================== TIER FAST ($0.50-$1.00) - min_gpu_ram: 24 ====================
  // 9 offers (3 US, 3 EU, 3 ASIA)
  { id: 1018, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24, cpu_cores: 12, cpu_ram: 48, disk_space: 150, dph_total: 0.55, inet_down: 1200, verified: true, geolocation: 'US' },
  { id: 1019, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24, cpu_cores: 14, cpu_ram: 64, disk_space: 180, dph_total: 0.60, inet_down: 1300, verified: true, geolocation: 'EU' },
  { id: 1009, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24, cpu_cores: 16, cpu_ram: 64, disk_space: 200, dph_total: 0.65, inet_down: 1500, verified: true, geolocation: 'EU' },
  { id: 1010, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24, cpu_cores: 24, cpu_ram: 128, disk_space: 500, dph_total: 0.70, inet_down: 2000, verified: true, geolocation: 'US' },
  { id: 1020, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24, cpu_cores: 20, cpu_ram: 96, disk_space: 300, dph_total: 0.80, inet_down: 1800, verified: true, geolocation: 'EU' },
  { id: 1021, gpu_name: 'A5000', num_gpus: 1, gpu_ram: 24, cpu_cores: 16, cpu_ram: 64, disk_space: 250, dph_total: 0.85, inet_down: 1500, verified: true, geolocation: 'US' },
  { id: 1031, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24, cpu_cores: 12, cpu_ram: 48, disk_space: 150, dph_total: 0.52, inet_down: 1100, verified: true, geolocation: 'ASIA' },
  { id: 1032, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24, cpu_cores: 16, cpu_ram: 64, disk_space: 200, dph_total: 0.68, inet_down: 1400, verified: true, geolocation: 'ASIA' },
  { id: 1033, gpu_name: 'A5000', num_gpus: 1, gpu_ram: 24, cpu_cores: 14, cpu_ram: 64, disk_space: 200, dph_total: 0.75, inet_down: 1300, verified: true, geolocation: 'ASIA' },

  // ==================== TIER ULTRA (> $1.00) - min_gpu_ram: 40 ====================
  // 9 offers (3 US, 3 EU, 3 ASIA)
  { id: 1011, gpu_name: 'A6000', num_gpus: 1, gpu_ram: 48, cpu_cores: 32, cpu_ram: 128, disk_space: 500, dph_total: 1.00, inet_down: 2000, verified: true, geolocation: 'US' },
  { id: 1022, gpu_name: 'A6000', num_gpus: 1, gpu_ram: 48, cpu_cores: 24, cpu_ram: 96, disk_space: 400, dph_total: 1.10, inet_down: 1800, verified: true, geolocation: 'EU' },
  { id: 1023, gpu_name: 'A100 40GB', num_gpus: 1, gpu_ram: 40, cpu_cores: 32, cpu_ram: 128, disk_space: 500, dph_total: 1.50, inet_down: 3000, verified: true, geolocation: 'EU' },
  { id: 1024, gpu_name: 'A100 40GB', num_gpus: 1, gpu_ram: 40, cpu_cores: 48, cpu_ram: 192, disk_space: 800, dph_total: 2.00, inet_down: 4000, verified: true, geolocation: 'US' },
  { id: 1012, gpu_name: 'A100 80GB', num_gpus: 1, gpu_ram: 80, cpu_cores: 64, cpu_ram: 256, disk_space: 1000, dph_total: 2.50, inet_down: 5000, verified: true, geolocation: 'EU' },
  { id: 1013, gpu_name: 'H100 80GB', num_gpus: 1, gpu_ram: 80, cpu_cores: 96, cpu_ram: 512, disk_space: 2000, dph_total: 4.00, inet_down: 10000, verified: true, geolocation: 'US' },
  { id: 1034, gpu_name: 'A6000', num_gpus: 1, gpu_ram: 48, cpu_cores: 24, cpu_ram: 96, disk_space: 400, dph_total: 1.05, inet_down: 1700, verified: true, geolocation: 'ASIA' },
  { id: 1035, gpu_name: 'A100 40GB', num_gpus: 1, gpu_ram: 40, cpu_cores: 32, cpu_ram: 128, disk_space: 500, dph_total: 1.80, inet_down: 3500, verified: true, geolocation: 'ASIA' },
  { id: 1036, gpu_name: 'A100 80GB', num_gpus: 1, gpu_ram: 80, cpu_cores: 48, cpu_ram: 192, disk_space: 800, dph_total: 3.00, inet_down: 6000, verified: true, geolocation: 'ASIA' },
];

export const DEFAULT_FILTERS = {
  // GPU
  gpu_name: 'any',
  num_gpus: 1,
  min_gpu_ram: 0,
  gpu_frac: 1,
  gpu_mem_bw: 0,
  gpu_max_power: 0,
  bw_nvlink: 0,
  // CPU & Memória & Armazenamento
  min_cpu_cores: 1,
  min_cpu_ram: 1,
  min_disk: 50,
  cpu_ghz: 0,
  // Performance
  min_dlperf: 0,
  min_pcie_bw: 0,
  total_flops: 0,
  cuda_vers: 'any',
  compute_cap: 0,
  // Rede
  min_inet_down: 100,
  min_inet_up: 50,
  direct_port_count: 0,
  // Preço
  max_price: 5.0,
  rental_type: 'on-demand',
  // Qualidade & Localização
  min_reliability: 0,
  region: 'any',
  verified_only: false,
  datacenter: false,
  // Opções avançadas
  static_ip: false,
  // Ordenação
  order_by: 'dph_total',
  limit: 100
};
