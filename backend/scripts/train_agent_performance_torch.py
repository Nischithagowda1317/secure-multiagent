from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from _bootstrap import PROJECT_ROOT
from app.ml.features import HITL_CATEGORICAL, HITL_NUMERIC
from training_common import save_metrics


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def train(epochs: int, patience: int, batch_size: int, force: bool, resume: bool) -> None:
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError as exc:
        raise SystemExit(
            "PyTorch is not installed. Install a build matching your CUDA version, then rerun this script."
        ) from exc

    class PerformanceMLP(nn.Module):
        def __init__(self, input_dim: int):
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.ReLU(),
                nn.BatchNorm1d(128),
                nn.Dropout(0.20),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Dropout(0.15),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
            )

        def forward(self, x):
            return self.network(x).squeeze(1)

    seed = 42
    set_seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model_dir = PROJECT_ROOT / "models" / "agent_performance_nn"
    checkpoint_dir = PROJECT_ROOT / "runtime" / "checkpoints" / "agent_performance_nn"
    best_path = model_dir / "best_model.pt"
    preprocessor_path = model_dir / "preprocessor.joblib"
    checkpoint_path = checkpoint_dir / "latest.pt"
    if best_path.exists() and not force and not (resume and checkpoint_path.exists()):
        print(
            f"[SKIP] Neural model already exists: {best_path}. "
            "Use --force --no-resume for a fresh run."
        )
        return
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(
        PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset" / "raw_sources" / "agentic_ai_performance_source.csv"
    )
    x = data[HITL_NUMERIC + HITL_CATEGORICAL]
    y = data["performance_index"].astype(np.float32).to_numpy()
    x_train_raw, x_temp_raw, y_train, y_temp = train_test_split(
        x, y, test_size=0.30, random_state=seed
    )
    x_val_raw, x_test_raw, y_val, y_test = train_test_split(
        x_temp_raw, y_temp, test_size=0.50, random_state=seed
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", StandardScaler(), HITL_NUMERIC),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                HITL_CATEGORICAL,
            ),
        ],
        sparse_threshold=0,
    )
    x_train = preprocessor.fit_transform(x_train_raw).astype(np.float32)
    x_val = preprocessor.transform(x_val_raw).astype(np.float32)
    x_test = preprocessor.transform(x_test_raw).astype(np.float32)
    joblib.dump(preprocessor, preprocessor_path)

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train)),
        batch_size=batch_size,
        shuffle=True,
        pin_memory=torch.cuda.is_available(),
    )
    val_x = torch.from_numpy(x_val).to(device)
    val_y = torch.from_numpy(y_val).to(device)
    model = PerformanceMLP(x_train.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.MSELoss()
    start_epoch = 1
    best_val = float("inf")
    epochs_without_improvement = 0
    history: list[dict[str, float]] = []

    if resume and checkpoint_path.exists() and not force:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        start_epoch = int(checkpoint["epoch"]) + 1
        best_val = float(checkpoint["best_val_loss"])
        epochs_without_improvement = int(checkpoint.get("epochs_without_improvement", 0))
        history = checkpoint.get("history", [])
        print(f"[RESUME] Continuing from epoch {start_epoch}")

    for epoch in range(start_epoch, epochs + 1):
        model.train()
        train_losses = []
        for features, target in train_loader:
            features = features.to(device, non_blocking=True)
            target = target.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            prediction = model(features)
            loss = criterion(prediction, target)
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))
        model.eval()
        with torch.no_grad():
            val_prediction = model(val_x)
            val_loss = float(criterion(val_prediction, val_y).cpu())
        train_loss = float(np.mean(train_losses))
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})
        improved = val_loss < best_val - 1e-6
        if improved:
            best_val = val_loss
            epochs_without_improvement = 0
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "input_dim": x_train.shape[1],
                    "best_val_loss": best_val,
                    "epoch": epoch,
                    "device_used": str(device),
                    "feature_columns": HITL_NUMERIC + HITL_CATEGORICAL,
                },
                best_path,
            )
        else:
            epochs_without_improvement += 1
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "best_val_loss": best_val,
                "epochs_without_improvement": epochs_without_improvement,
                "history": history,
                "input_dim": x_train.shape[1],
            },
            checkpoint_path,
        )
        print(
            f"Epoch {epoch:03d} | train_loss={train_loss:.6f} | "
            f"val_loss={val_loss:.6f} | best={best_val:.6f}"
        )
        if epochs_without_improvement >= patience:
            print(f"[EARLY STOP] No validation improvement for {patience} epochs.")
            break

    best = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(best["model_state_dict"])
    model.eval()
    with torch.no_grad():
        predictions = model(torch.from_numpy(x_test).to(device)).cpu().numpy()
    metrics = {
        "model": "PyTorch MLP agent performance-index regressor",
        "device_used": str(device),
        "cuda_available": bool(torch.cuda.is_available()),
        "epochs_requested": epochs,
        "epochs_completed": history[-1]["epoch"] if history else 0,
        "best_epoch": int(best["epoch"]),
        "best_validation_loss": float(best["best_val_loss"]),
        "test_mae": float(mean_absolute_error(y_test, predictions)),
        "test_rmse": float(mean_squared_error(y_test, predictions) ** 0.5),
        "test_r2": float(r2_score(y_test, predictions)),
        "checkpoint_path": str(checkpoint_path.relative_to(PROJECT_ROOT)),
        "best_model_path": str(best_path.relative_to(PROJECT_ROOT)),
        "resume_supported": True,
        "history_tail": history[-10:],
    }
    save_metrics(model_dir / "metrics.json", metrics)
    (model_dir / "config.json").write_text(
        json.dumps(
            {
                "input_dim": x_train.shape[1],
                "hidden_layers": [128, 64, 32],
                "dropout": [0.20, 0.15],
                "target": "performance_index",
                "numeric_features": HITL_NUMERIC,
                "categorical_features": HITL_CATEGORICAL,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[OK] Best neural model saved to {best_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    train(args.epochs, args.patience, args.batch_size, args.force, not args.no_resume)
