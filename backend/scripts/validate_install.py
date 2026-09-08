from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from _bootstrap import PROJECT_ROOT


REQUIRED_MODULES = [
    "fastapi",
    "uvicorn",
    "pandas",
    "numpy",
    "sklearn",
    "joblib",
    "jwt",
    "docx",
    "fitz",
    "openpyxl",
    "httpx",
]

REQUIRED_ARTIFACTS = [
    "models/router/router_model.joblib",
    "models/workload/workload_model.joblib",
    "models/task_risk/task_risk_model.joblib",
    "models/sales_approval/sales_approval_model.joblib",
    "models/hitl/hitl_model.joblib",
    "models/agent_performance/agent_performance_model.joblib",
    "models/rag/rag_index.joblib",
    "models/reports/system_evaluation.json",
]


def main() -> None:
    dataset_root = PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset"
    checks: dict[str, object] = {
        "python_version": sys.version.split()[0],
        "python_3_11_or_newer": sys.version_info >= (3, 11),
        "dataset_present": (dataset_root / "README.md").exists(),
        "dataset_validation_present": (dataset_root / "validation_report.json").exists(),
        "frontend_built": (PROJECT_ROOT / "frontend" / "dist" / "index.html").exists(),
        "knowledge_pdf_count": len(list((dataset_root / "knowledge_base" / "canonical_pdf").glob("*.pdf"))),
        "knowledge_docx_count": len(list((dataset_root / "knowledge_base" / "editable_docx").glob("*.docx"))),
    }
    for module in REQUIRED_MODULES:
        try:
            imported = importlib.import_module(module)
            checks[f"module_{module}"] = True
            version = getattr(imported, "__version__", None)
            if version:
                checks[f"version_{module}"] = str(version)
        except Exception as exc:
            checks[f"module_{module}"] = False
            checks[f"module_{module}_error"] = str(exc)

    try:
        importlib.import_module("langgraph")
        checks["optional_langgraph_available"] = True
    except Exception:
        checks["optional_langgraph_available"] = False
        checks["optional_langgraph_note"] = (
            "The deterministic workflow fallback is active. Installing backend/requirements.txt "
            "normally adds LangGraph."
        )

    missing_artifacts = []
    for relative in REQUIRED_ARTIFACTS:
        if not (PROJECT_ROOT / relative).exists():
            missing_artifacts.append(relative)
    checks["required_model_artifacts"] = len(REQUIRED_ARTIFACTS)
    checks["missing_required_artifacts"] = missing_artifacts
    checks["optional_neural_model_present"] = (
        PROJECT_ROOT / "models" / "agent_performance_nn" / "best_model.pt"
    ).exists()
    checks["trained_model_count"] = len(
        list((PROJECT_ROOT / "models").glob("**/*.joblib"))
        + list((PROJECT_ROOT / "models").glob("**/*.pt"))
    )

    boolean_checks = [
        value
        for key, value in checks.items()
        if isinstance(value, bool)
        and key not in {"optional_neural_model_present", "optional_langgraph_available"}
    ]
    checks["all_required_checks_passed"] = (
        all(boolean_checks)
        and not missing_artifacts
        and checks["knowledge_pdf_count"] >= 1
        and checks["knowledge_docx_count"] >= 1
    )
    print(json.dumps(checks, indent=2))
    if not checks["all_required_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
