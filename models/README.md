# Model Artifacts

This folder contains ready-to-run academic model artifacts and evaluation files.

- `.joblib`: scikit-learn pipeline or retrieval index
- `.pt`: optional PyTorch checkpoint/model
- `metrics.json`: test or evaluation metrics
- `model_manifest.json`: SHA-256 integrity manifest

Run `train_models.ps1 -Force` to recreate conventional artifacts. Run `train_gpu_model.ps1` for the optional neural model.
