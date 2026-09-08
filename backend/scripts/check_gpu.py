from __future__ import annotations

import json


def main() -> None:
    try:
        import torch
    except ImportError:
        print(json.dumps({"torch_installed": False}, indent=2))
        raise SystemExit(1)
    payload = {
        "torch_installed": True,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "torch_cuda_version": torch.version.cuda,
        "device_count": torch.cuda.device_count(),
        "devices": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
