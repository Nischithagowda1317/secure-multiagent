from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _bootstrap import PROJECT_ROOT


SCRIPTS = [
    "train_router.py",
    "train_workload.py",
    "train_task_risk.py",
    "train_sales_approval.py",
    "train_hitl.py",
    "train_agent_performance.py",
    "build_rag_index.py",
]


def main(force: bool, include_neural: bool, neural_epochs: int) -> None:
    scripts_dir = PROJECT_ROOT / "backend" / "scripts"
    for script in SCRIPTS:
        command = [sys.executable, str(scripts_dir / script)]
        if force:
            command.append("--force")
        print("\n" + "=" * 78, flush=True)
        print(f"Running {script}", flush=True)
        print("=" * 78, flush=True)
        subprocess.check_call(command, cwd=PROJECT_ROOT)
    if include_neural:
        command = [
            sys.executable,
            str(scripts_dir / "train_agent_performance_torch.py"),
            "--epochs",
            str(neural_epochs),
        ]
        if force:
            command.append("--force")
        subprocess.check_call(command, cwd=PROJECT_ROOT)
    subprocess.check_call(
        [sys.executable, str(scripts_dir / "evaluate_system.py")], cwd=PROJECT_ROOT
    )
    subprocess.check_call(
        [sys.executable, str(scripts_dir / "generate_model_manifest.py")],
        cwd=PROJECT_ROOT,
    )
    print("\nAll requested training, evaluation, and manifest stages completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train all production models. Existing artifacts are skipped so an interrupted run can be resumed."
    )
    parser.add_argument("--force", action="store_true", help="Retrain and overwrite existing artifacts")
    parser.add_argument("--include-neural", action="store_true", help="Also train the optional PyTorch model")
    parser.add_argument("--neural-epochs", type=int, default=100)
    args = parser.parse_args()
    main(args.force, args.include_neural, args.neural_epochs)
