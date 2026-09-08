# Project Implementation Checklist

## Environment

- [ ] Extract the ZIP.
- [ ] Install Python 3.11+.
- [ ] Run `setup_and_train.ps1`.
- [ ] Confirm automated tests pass.
- [ ] Run `run_dashboard.ps1`.

## Core demonstration

- [ ] Login works.
- [ ] Dashboard KPIs load.
- [ ] Policy RAG returns source evidence.
- [ ] Project + HR multi-agent query works.
- [ ] Sales analysis works.
- [ ] Unauthorized salary query is denied.
- [ ] Sensitive task reassignment creates approval.
- [ ] Approval can be reviewed by an authorized role.
- [ ] Audit page shows runtime events.
- [ ] Models page shows artifacts and metrics.

## Training evidence

- [ ] Save console output or screenshot of model training.
- [ ] Show model files under `models`.
- [ ] Show metrics JSON files.
- [ ] Show `model_manifest.json` checksums.
- [ ] Optionally demonstrate GPU and checkpoint resume.

## Report evidence

- [ ] Architecture diagram matches implemented agents.
- [ ] Dataset mapping names the exact files.
- [ ] Explain that task-risk labels are synthetic/deterministic.
- [ ] Report security and RAG evaluation separately.
- [ ] Include limitations and future external-system integration.
