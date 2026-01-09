import os
import structlog
from py3nvml import py3nvml

logger = structlog.get_logger(__name__)

def get_gpu_metrics():
    """
    Returns GPU utilization and memory usage using py3nvml.
    Returns zeroed values with status 'Unavailable' if GPU is not available or drivers are missing.
    """
    try:
        py3nvml.nvmlInit()
        handle = py3nvml.nvmlDeviceGetHandleByIndex(0)
        util = py3nvml.nvmlDeviceGetUtilizationRates(handle)
        mem = py3nvml.nvmlDeviceGetMemoryInfo(handle)
        
        metrics = {
            "gpu_utilization": util.gpu,
            "memory_utilization": int((mem.used / mem.total) * 100),
            "memory_used_mb": int(mem.used / (1024 * 1024)),
            "memory_total_mb": int(mem.total / (1024 * 1024)),
            "status": "Healthy"
        }
        py3nvml.nvmlShutdown()
        return metrics
    except Exception as e:
        logger.warning("gpu_metrics_failed", error=str(e))
        return {
            "gpu_utilization": 0,
            "memory_utilization": 0,
            "memory_used_mb": 0,
            "memory_total_mb": 0,
            "status": "Unavailable",
            "error": str(e)
        }

if __name__ == "__main__":
    print(get_gpu_metrics())
