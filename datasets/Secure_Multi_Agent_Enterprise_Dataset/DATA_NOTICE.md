# Data Notice and Responsible-Use Notes

## Synthetic curated data

All data under `core/` and `knowledge_base/` was created or normalized for a fictional company named NexaCore Technologies. It does not describe a real employer, employee population, customer portfolio, project, financial position, or security program.

The curated data may be used for:

- Academic projects and demonstrations
- Local software development and testing
- RAG, agent-routing, RBAC, HITL, and evaluation experiments
- Dashboards, SQL practice, and proof-of-concept applications

It should not be used for:

- Real employment, compensation, credit, insurance, disciplinary, or eligibility decisions
- Real financial approval
- Production security configuration without expert review
- Claims that relationships in the data are causal

## Raw uploaded sources

The original files supplied in the conversation are retained under `raw_sources/` for traceability. They may have their own source terms or licences. Review the original source conditions before public redistribution or commercial use.

Two uploaded agent-performance files were byte-identical. The package retains only one copy and includes `raw_sources/DUPLICATE_FILE_NOTE.txt`.

## Privacy and credentials

The package contains only synthetic demonstration identities in the curated data. `demo_credentials.csv` contains a deliberately shared temporary password for local testing. Do not use that password in a real deployment and do not publish a running application that accepts it.

## AI safety

- Enforce permissions in deterministic backend code.
- Filter RAG data before it reaches the model.
- Treat documents and attachments as untrusted content.
- Require human approval for sensitive changes.
- Log both allowed and denied actions.
- Do not expose private chain-of-thought reasoning; provide concise evidence and workflow explanations instead.
