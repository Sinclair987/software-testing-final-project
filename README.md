# Software Testing and Maintenance Final Project

This repository contains the course final project for reproducing monitoring,
testing, fault-injection, and KPI-root-cause-localization experiments on
JoinFyc/Online-Boutique.

## Project Scope

- Microservice system: JoinFyc/Online-Boutique
- Local cluster: Minikube
- Monitoring: Prometheus, Grafana, Blackbox Exporter
- Fault injection: ChaosMesh
- Black-box testing: Selenium and JMeter
- Paper reproduction: ISSRE24-KPIRoot

The downloaded papers and course requirement PDFs are intentionally excluded
from version control. The upstream Online-Boutique source is also excluded and
should be cloned from its original repository when needed.

## Directory Layout

```text
chaos/       ChaosMesh manifests used in Phase 2
data/        Collected experiment data and generated results
docs/        Phase-by-phase execution notes
grafana/     Grafana dashboard JSON
monitoring/  Monitoring manifests
scripts/     Deployment, monitoring, test, and reproduction runners
src/         Python implementation of KPIRoot reproduction
tests/       Selenium, JMeter, and KPIRoot tests
```

## Phase 4 KPIRoot Reproduction

The reproduction code is under `src/kpiroot/`. It implements:

1. KPI matrix loading and cleaning.
2. Synthetic alarm KPI construction.
3. PAA and SAX representation.
4. Fault-window segment selection.
5. SAX-Jaccard similarity scoring.
6. Granger-style causality scoring.
7. KPIRoot combined ranking and ablation comparison.

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-phase4-kpiroot.ps1
```

Outputs:

```text
data/phase4/kpiroot/summary.csv
data/phase4/kpiroot/ablation_summary.csv
data/phase4/kpiroot/<scenario>/ranking.csv
data/phase4/kpiroot/<scenario>/topk_scores.png
data/phase4/kpiroot/<scenario>/alarm_top_candidates.png
docs/PHASE4_KPIROOT.md
```

## Verification

Run the KPIRoot unit tests:

```powershell
.\.conda\python.exe -m pytest .\tests\kpiroot -v -o "cache_dir=.pytest_cache"
```

The full Selenium suite requires the Online-Boutique frontend to be available
at `http://127.0.0.1:8088`.

## Notes

- The Phase 4 reproduction adapts KPIRoot from Cloud H host/VM KPIs to
  Online-Boutique service-level KPIs.
- The CPU stress scenarios are the strongest evidence for KPIRoot because the
  aggregate CPU alarm naturally maps to service CPU root causes.
- The Pod Kill scenario is retained as a boundary case because processed
  service-level data hides some Pod identity changes.
