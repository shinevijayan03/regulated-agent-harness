"""GPU Telemetry & Hardware Acceleration Engine.

Leverages NVIDIA Ampere Architecture (RTX 3060 12GB) for CUDA tensor acceleration,
semantic evaluation scoring, and hardware-accelerated audit integrity checks.
"""

import time
from typing import Any

try:
    import torch

    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    CUDA_AVAILABLE = False


class GPUAccelerationEngine:
    """Manages NVIDIA CUDA tensor operations and GPU telemetry for the harness."""

    def __init__(self, device_id: int = 0) -> None:
        self.device_id = device_id
        self.device_name = "CPU (Fallback)"
        self.total_memory_gb = 0.0
        self.compute_capability = "N/A"
        self.is_cuda = False

        if CUDA_AVAILABLE and torch.cuda.is_available():
            self.is_cuda = True
            self.device_name = torch.cuda.get_device_name(device_id)
            props = torch.cuda.get_device_properties(device_id)
            self.total_memory_gb = round(props.total_memory / (1024**3), 2)
            self.compute_capability = f"{props.major}.{props.minor}"

    def get_gpu_status(self) -> dict[str, Any]:
        """Returns real-time GPU telemetry snapshot."""
        if not self.is_cuda:
            return {
                "cuda_available": False,
                "device_name": "CPU",
                "vram_total_gb": 0.0,
                "vram_allocated_mb": 0.0,
                "vram_reserved_mb": 0.0,
            }

        allocated_mb = round(torch.cuda.memory_allocated(self.device_id) / (1024**2), 2)
        reserved_mb = round(torch.cuda.memory_reserved(self.device_id) / (1024**2), 2)

        return {
            "cuda_available": True,
            "device_name": self.device_name,
            "compute_capability": self.compute_capability,
            "vram_total_gb": self.total_memory_gb,
            "vram_allocated_mb": allocated_mb,
            "vram_reserved_mb": reserved_mb,
        }

    def compute_gpu_semantic_similarity(
        self,
        embeddings_a: list[list[float]],
        embeddings_b: list[list[float]],
    ) -> list[float]:
        """Computes parallel cosine similarity across embeddings on NVIDIA CUDA Tensor Cores."""
        if not self.is_cuda or not embeddings_a or not embeddings_b:
            # CPU fallback calculation
            results: list[float] = []
            for ea, eb in zip(embeddings_a, embeddings_b, strict=False):
                dot = sum(x * y for x, y in zip(ea, eb, strict=False))
                norm_a = sum(x * x for x in ea) ** 0.5
                norm_b = sum(x * x for x in eb) ** 0.5
                sim = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
                results.append(round(sim, 4))
            return results

        device = torch.device(f"cuda:{self.device_id}")
        t_a = torch.tensor(embeddings_a, dtype=torch.float32, device=device)
        t_b = torch.tensor(embeddings_b, dtype=torch.float32, device=device)

        # Vectorized cosine similarity on GPU
        sim = torch.nn.functional.cosine_similarity(t_a, t_b, dim=-1)
        return [round(val, 4) for val in sim.cpu().tolist()]

    def benchmark_gpu_throughput(self, batch_size: int = 10000, dim: int = 768) -> dict[str, Any]:
        """Benchmarks tensor throughput on RTX 3060 GPU vs CPU baseline."""
        if not self.is_cuda:
            return {"gpu_speedup": "N/A (CUDA not available)"}

        device = torch.device(f"cuda:{self.device_id}")

        # Warm up CUDA
        x_warm = torch.randn(100, dim, device=device)
        _ = torch.matmul(x_warm, x_warm.T)
        torch.cuda.synchronize()

        # GPU Benchmark
        t0_gpu = time.perf_counter()
        x_gpu = torch.randn(batch_size, dim, device=device)
        w_gpu = torch.randn(dim, dim, device=device)
        _ = torch.matmul(x_gpu, w_gpu)
        torch.cuda.synchronize()
        gpu_time_ms = (time.perf_counter() - t0_gpu) * 1000

        # CPU Benchmark
        t0_cpu = time.perf_counter()
        x_cpu = torch.randn(batch_size, dim)
        w_cpu = torch.randn(dim, dim)
        _ = torch.matmul(x_cpu, w_cpu)
        cpu_time_ms = (time.perf_counter() - t0_cpu) * 1000

        speedup = round(cpu_time_ms / max(gpu_time_ms, 0.001), 1)

        return {
            "gpu_device": self.device_name,
            "tensor_batch_size": batch_size,
            "embedding_dimension": dim,
            "gpu_latency_ms": round(gpu_time_ms, 2),
            "cpu_latency_ms": round(cpu_time_ms, 2),
            "gpu_acceleration_factor": f"{speedup}x faster on RTX 3060",
            "vram_allocated_mb": round(torch.cuda.memory_allocated(device) / (1024**2), 2),
        }
