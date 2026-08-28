# RetailPulse — End-to-End Demand Forecasting & Anomaly Detection Platform

> A mini version of a real analytics-consulting client engagement: ingest real-time + batch retail/IoT data, land it in a lakehouse, enrich it with a knowledge graph, forecast demand, detect anomalies (stockouts/fraud), and serve everything through a self-serve BI dashboard.

## Why this project exists
This project is being built as a portfolio / resume piece that demonstrates the full data-to-decision lifecycle referenced in analytics-consulting job descriptions (cloud-native + cloud-agnostic stacks, PySpark, streaming + batch, knowledge graphs, lakehouses, ML forecasting, microservices, BI dashboards).

## Document index
| File | Purpose |
|---|---|
| `PRD.md` | Product requirements — problem, users, goals, success metrics, scope |
| `ARCHITECTURE.md` | System architecture, data flow, component diagram (as text), deployment topology |
| `FEATURES.md` | Feature list broken into MVP / V2 / stretch, with acceptance criteria |
| `TECH_STACK.md` | Every technology, why it was chosen, and the JD phrase it maps to |
| `IMPLEMENTATION.md` | Build order, module-by-module implementation notes, data contracts |
| `UI_DESIGN.md` | Dashboard design spec derived from the reference screenshot |
| `TASKS.md` | Checklist-style task breakdown, phased, for Antigravity to execute |
| `API_REFERENCE.md` | External APIs, endpoints, and env vars/URLs the agent will need |

## Suggested build order
1. Read `PRD.md` and `ARCHITECTURE.md` for context.
2. Follow `TASKS.md` top to bottom — it is phased and each phase is independently demoable.
3. Use `TECH_STACK.md` + `API_REFERENCE.md` whenever a task references an external service.
4. Use `UI_DESIGN.md` when building the dashboard (Phase 6).

## Recommended scope for a resume-ready v1
Building all 10 tools shallowly is worse than a tight, working core. The **MVP core** is:
`PySpark → Delta Lake (lakehouse) → XGBoost forecasting → FastAPI → Streamlit dashboard`,
with Kafka, Neo4j, and Postgres/Snowflake added as **Phase 2** once the core works end-to-end.
See `FEATURES.md` for the MVP/V2 split and `TASKS.md` Phase markers.
