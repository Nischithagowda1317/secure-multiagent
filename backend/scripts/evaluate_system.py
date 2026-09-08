from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from _bootstrap import PROJECT_ROOT
from app.security.rbac import RBACService
from app.services.repository import DataRepository
from app.services.runtime_store import RuntimeStore
from app.settings import settings
from app.utils.text import pipe_values
from training_common import save_metrics


def main() -> None:
    dataset = PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset"
    report: dict = {}

    router_path = PROJECT_ROOT / "models" / "router" / "router_model.joblib"
    routing = pd.read_csv(dataset / "core" / "evaluation" / "routing_test_cases.csv")
    if router_path.exists():
        router = joblib.load(router_path)
        predictions = router.predict(routing["input_text"].astype(str))
        report["router_full_dataset_accuracy"] = float(
            (predictions == routing["expected_workflow_definition_id"].astype(str)).mean()
        )
        report["routing_cases"] = int(len(routing))

    rag_path = PROJECT_ROOT / "models" / "rag" / "rag_index.joblib"
    questions = pd.read_csv(dataset / "core" / "rag" / "rag_evaluation_questions.csv")
    role_permissions = pd.read_csv(dataset / "core" / "identity_access" / "role_permissions.csv")
    if rag_path.exists():
        index = joblib.load(rag_path)
        vectorizer, matrix, metadata = index["vectorizer"], index["matrix"], index["metadata"]
        top1 = top3 = allowed_cases = 0
        for _, row in questions.iterrows():
            if row["expected_security_decision"] != "ALLOW":
                continue
            allowed_cases += 1
            permissions = set(
                role_permissions.loc[
                    role_permissions["role_name"] == row["user_role"], "permission_name"
                ].astype(str)
            )
            scores = cosine_similarity(vectorizer.transform([str(row["question"])]), matrix)[0]
            ranked = scores.argsort()[::-1]
            documents = []
            for position in ranked:
                item = metadata[position]
                roles = set(pipe_values(item.get("allowed_roles")))
                required = str(item.get("required_permission") or "")
                if row["user_role"] not in roles or required not in permissions:
                    continue
                documents.append(str(item["document_id"]))
                if len(documents) == 3:
                    break
            expected = str(row["expected_document_id"])
            top1 += int(documents and documents[0] == expected)
            top3 += int(expected in documents)
        report["secure_rag_allowed_cases"] = allowed_cases
        report["secure_rag_top1_document_accuracy"] = top1 / max(allowed_cases, 1)
        report["secure_rag_top3_document_accuracy"] = top3 / max(allowed_cases, 1)

    repository = DataRepository(settings)
    runtime = RuntimeStore(PROJECT_ROOT / "runtime" / "evaluation_runtime.db")
    rbac = RBACService(runtime)
    security_tests = pd.read_csv(dataset / "core" / "evaluation" / "security_test_cases.csv")
    correct = 0
    checked = 0
    for _, row in security_tests.iterrows():
        # The matrix expresses role/permission expectations directly, so construct a role-scoped user.
        role = str(row["user_role"])
        permissions = repository.role_permission_map.get(role, set())
        result = rbac.authorize(
            user={
                "user_id": f"TEST-{role}",
                "roles": [role],
                "permissions": sorted(permissions),
                "mfa_enabled": True,
            },
            permission=str(row["requested_permission"]),
            resource_type="evaluation_resource",
            input_text="security matrix evaluation",
        )
        expected = str(row["expected_decision"])
        correct += int(result.decision.decision == expected)
        checked += 1
    report["security_cases"] = checked
    report["security_decision_accuracy"] = correct / max(checked, 1)

    output = PROJECT_ROOT / "models" / "reports" / "system_evaluation.json"
    save_metrics(output, report)
    print(json.dumps(report, indent=2))
    print(f"[OK] Evaluation report saved to {output}")


if __name__ == "__main__":
    main()
