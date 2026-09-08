# Security Design and Limitations

## Security controls implemented

- JWT authentication;
- role-to-permission mapping;
- deterministic RBAC authorization before protected reads/actions;
- role and permission filtering before RAG evidence is returned;
- prompt-injection pattern detection;
- file extension and upload-size validation;
- Human-in-the-Loop approval for sensitive actions;
- audit events for login, denial, upload and approval decisions;
- local/offline extractive answer mode;
- optional local Ollama use instead of sending enterprise evidence to a remote provider.

## Academic implementation limitations

1. Demo credentials are intentionally included and must never be used in production.
2. JWT storage and browser hardening are suitable for a prototype, not a final commercial security review.
3. Runtime state uses SQLite by default and is not designed for multi-server concurrency.
4. The dataset is synthetic; model metrics do not demonstrate real-world generalization.
5. The project simulates enterprise tools using controlled datasets rather than directly modifying SAP, Salesforce, Workday or Jira.
6. Approval completion records the decision; it does not call an external enterprise transaction API.
7. The extractive fallback is deterministic but less conversational than a generative LLM.
8. Prompt-injection detection is defensive pattern checking, not a proof of complete protection.
9. Uploaded scanned images need OCR, which is not enabled by default.
10. The optional neural model predicts a synthetic agent-performance index and is not necessary for core workflow execution.

## Report wording to use

A correct claim is:

> The prototype demonstrates secure multi-agent orchestration, role-aware retrieval, explainable decision support and Human-in-the-Loop controls over a coherent synthetic enterprise environment.

Avoid claiming:

> The model is production-ready, perfectly secure, or validated across real companies.
