# Task

`LDD[mode=architect, creativity=conservative]:` design a staff-rota service for our hospital network.

**Scale:** 200 hospitals, ~40 000 nurses / doctors total, ~5 000 shift-changes per week.

**Enterprise constraints:**
- Strict "no new tech" policy — nothing that isn't already in our codebase
- Team: 2 engineers (1 mid-level + 1 junior)
- MVP ship deadline: **4 weeks**
- Regulatory: HIPAA. Auditable changes required; audit log retention 7 years
- Deploy target: on-prem Kubernetes (GKE Anthos), no public cloud direct-write
- 24/7 on-call rotation of 3 SREs

**Existing stack (what's already in the codebase):**
- Python 3.11, FastAPI
- PostgreSQL 15
- Celery + Redis for async work
- React + TypeScript for internal UIs
- ELK (Elasticsearch/Logstash/Kibana) for logs
- Prometheus + Grafana for metrics
- Helm charts for all deployments

Deliver the architecture under the **conservative** creativity level. The choice of level is not negotiable — do not decide to escalate to `standard` or `inventive` mid-run.

Emit the full LDD trace block with:
- `mode: architect, creativity: conservative` in the header
- `Loss-fn : L = rubric_violations + λ · novelty_penalty` line
- All 5 phases reported as they complete
- 11-item rubric score (standard 10 + item #11 novelty-penalty)
- Hand-off line on close

Also append trace lines to `.ldd/trace.log` (create the directory). When done, write `run-summary.md`.
