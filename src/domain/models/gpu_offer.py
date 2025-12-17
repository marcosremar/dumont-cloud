"""
Domain model for GPU offers
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GpuOffer:
    """Represents a GPU offer from a provider"""
    id: int
    gpu_name: str
    num_gpus: int
    gpu_ram: float  # GB
    cpu_cores: int
    cpu_ram: float  # GB
    disk_space: float  # GB
    inet_down: float  # Mbps
    inet_up: float  # Mbps
    dph_total: float  # Price per hour
    geolocation: str
    reliability: float
    cuda_version: str
    verified: bool
    static_ip: bool

    # Custos adicionais
    storage_cost: Optional[float] = None
    inet_up_cost: Optional[float] = None
    inet_down_cost: Optional[float] = None

    # Identificadores do host
    machine_id: Optional[int] = None
    hostname: Optional[str] = None

    # Campos de performance (novos)
    total_flops: Optional[float] = None      # TFLOPS total da GPU
    dlperf: Optional[float] = None           # Deep learning performance score
    dlperf_per_dphtotal: Optional[float] = None  # Eficiência DL (dlperf / preço)
    gpu_mem_bw: Optional[float] = None       # Memory bandwidth (GB/s)
    pcie_bw: Optional[float] = None          # PCIe bandwidth (GB/s)

    # Tipo de máquina e duração
    machine_type: str = "on-demand"          # on-demand, interruptible, bid
    min_bid: Optional[float] = None          # Bid mínimo (se tipo bid)
    duration: Optional[float] = None         # Duração mínima de aluguel (horas)

    # Métricas calculadas de custo-benefício
    cost_per_tflops: Optional[float] = None  # $/TFLOPS
    cost_per_gb_vram: Optional[float] = None # $/GB VRAM

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'gpu_name': self.gpu_name,
            'num_gpus': self.num_gpus,
            'gpu_ram': self.gpu_ram,
            'cpu_cores': self.cpu_cores,
            'cpu_ram': self.cpu_ram,
            'disk_space': self.disk_space,
            'inet_down': self.inet_down,
            'inet_up': self.inet_up,
            'dph_total': self.dph_total,
            'geolocation': self.geolocation,
            'reliability': self.reliability,
            'cuda_version': self.cuda_version,
            'verified': self.verified,
            'static_ip': self.static_ip,
            'storage_cost': self.storage_cost,
            'inet_up_cost': self.inet_up_cost,
            'inet_down_cost': self.inet_down_cost,
            'machine_id': self.machine_id,
            'hostname': self.hostname,
            # Novos campos
            'total_flops': self.total_flops,
            'dlperf': self.dlperf,
            'dlperf_per_dphtotal': self.dlperf_per_dphtotal,
            'gpu_mem_bw': self.gpu_mem_bw,
            'pcie_bw': self.pcie_bw,
            'machine_type': self.machine_type,
            'min_bid': self.min_bid,
            'duration': self.duration,
            'cost_per_tflops': self.cost_per_tflops,
            'cost_per_gb_vram': self.cost_per_gb_vram,
        }

    def calculate_efficiency_metrics(self):
        """Calcula métricas de custo-benefício."""
        if self.total_flops and self.total_flops > 0 and self.dph_total > 0:
            self.cost_per_tflops = self.dph_total / self.total_flops

        if self.gpu_ram and self.gpu_ram > 0 and self.dph_total > 0:
            self.cost_per_gb_vram = self.dph_total / self.gpu_ram

        if self.dlperf and self.dlperf > 0 and self.dph_total > 0:
            self.dlperf_per_dphtotal = self.dlperf / self.dph_total
