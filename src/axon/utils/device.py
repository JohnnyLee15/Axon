import torch


def get_torch_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.mps.is_available():
        return torch.device("mps")
    if torch.xpu.is_available():
        return torch.device("xpu")
    return torch.device("cpu")


def get_dtype() -> torch.dtype:
    if torch.cuda.is_available():
        return torch.float16
    if torch.mps.is_available():
        return torch.float16
    if torch.xpu.is_available():
        return torch.float16
    return torch.float32