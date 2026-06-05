# Phase 4: ISSRE24-KPIRoot Reproduction

Generated at: 2026-06-06T02:45:25

## Goal

This phase reproduces the core idea of ISSRE24-KPIRoot on the Online-Boutique monitoring data collected in Phase 2.
KPIRoot ranks candidate service KPIs by combining SAX-based similarity and Granger-causality scores.

## Mapping To Online-Boutique

- Alarm KPI: a system-level or synthetic aggregate KPI, such as `synthetic_total_cpu`.
- Candidate KPIs: service-level CPU, memory, filesystem, restart, and running-state series.
- Root cause: the service targeted by the ChaosMesh fault.

## Implemented Algorithm

1. Load and clean the exported Phase 2 KPI matrix.
2. Add synthetic aggregate alarm KPIs, including total CPU, total memory, unavailable Pods, and total restarts.
3. Normalize each KPI and compress it with Piecewise Aggregate Approximation (PAA).
4. Convert PAA values to Symbolic Aggregate Approximation (SAX) symbols.
5. Select the fault/anomaly window from scenario metadata, with automatic trend detection available as fallback.
6. Compute SAX multiset-Jaccard similarity between the alarm KPI and each candidate KPI.
7. Compute a Granger-style F statistic to estimate whether the candidate KPI precedes the alarm KPI.
8. Rank candidates by `0.9 * similarity + 0.1 * normalized_causality`, following the paper's lambda setting.

## Implementation Files

- `src/kpiroot/algorithm.py`: PAA, SAX, anomaly segment selection, similarity, causality, and ranking.
- `src/kpiroot/data.py`: Phase 2 data loading, metadata parsing, synthetic alarm construction, and expected-root extraction.
- `src/kpiroot/cli.py`: batch runner, evaluation, plotting, and report generation.
- `tests/kpiroot/test_algorithm.py`: focused unit tests for the reproduction implementation.
- `scripts/run-phase4-kpiroot.ps1`: project-level runner.

## Results

| Scenario | Alarm KPI | Expected Service | Top-1 KPI | Expected Service Rank | Hit@1 | Hit@3 | Hit@5 |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| pod-kill-paymentservice-001 | `synthetic_total_memory` | `paymentservice` | `memory__paymentservice` | 1 | yes | yes | yes |
| stress-frontend-cpu-001 | `synthetic_total_cpu` | `frontend` | `cpu__frontend` | 1 | yes | yes | yes |
| stress-paymentservice-cpu-001 | `synthetic_total_cpu` | `paymentservice` | `cpu__paymentservice` | 1 | yes | yes | yes |

## Ablation Study

The ablation study reuses the same KPI scores but changes the ranking objective:

- `similarity_only`: rank by SAX-Jaccard similarity only.
- `causality_only`: rank by normalized Granger causality only.
- `kpiroot_combined`: rank by `0.9 * similarity + 0.1 * normalized_causality`.

| Scenario | Method | Top-1 KPI | Expected Service Rank | Hit@1 | Hit@3 | Hit@5 |
| --- | --- | --- | ---: | --- | --- | --- |
| pod-kill-paymentservice-001 | `similarity_only` | `memory__paymentservice` | 1 | yes | yes | yes |
| pod-kill-paymentservice-001 | `causality_only` | `fs_writes__redis-cart` | 11 | no | no | no |
| pod-kill-paymentservice-001 | `kpiroot_combined` | `memory__paymentservice` | 1 | yes | yes | yes |
| stress-frontend-cpu-001 | `similarity_only` | `cpu__frontend` | 1 | yes | yes | yes |
| stress-frontend-cpu-001 | `causality_only` | `cpu__checkoutservice` | 9 | no | no | no |
| stress-frontend-cpu-001 | `kpiroot_combined` | `cpu__frontend` | 1 | yes | yes | yes |
| stress-paymentservice-cpu-001 | `similarity_only` | `cpu__paymentservice` | 1 | yes | yes | yes |
| stress-paymentservice-cpu-001 | `causality_only` | `memory__shippingservice` | 9 | no | no | no |
| stress-paymentservice-cpu-001 | `kpiroot_combined` | `cpu__paymentservice` | 1 | yes | yes | yes |

## Output Artifacts

- Summary CSV: `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\summary.csv`
- Ablation summary CSV: `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\ablation_summary.csv`
- Per-scenario files:
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\pod-kill-paymentservice-001\ranking.csv`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\pod-kill-paymentservice-001\ablation_summary.csv`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\pod-kill-paymentservice-001\topk_scores.png`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\pod-kill-paymentservice-001\alarm_top_candidates.png`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\stress-frontend-cpu-001\ranking.csv`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\stress-frontend-cpu-001\ablation_summary.csv`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\stress-frontend-cpu-001\topk_scores.png`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\stress-frontend-cpu-001\alarm_top_candidates.png`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\stress-paymentservice-cpu-001\ranking.csv`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\stress-paymentservice-cpu-001\ablation_summary.csv`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\stress-paymentservice-cpu-001\topk_scores.png`
  - `D:\Study\SoftwareTesting\FinalProject\data\phase4\kpiroot\stress-paymentservice-cpu-001\alarm_top_candidates.png`

## Notes

- The original paper evaluates Cloud H host-cluster and VM KPIs. This project adapts the method to service-level Online-Boutique KPIs.
- The paper uses very large industrial time series. Our course datasets are short, so the implementation keeps more PAA bins than sqrt(n) by default.
- In the ablation results, causality-only ranking is unstable on these short time series, while SAX similarity and the combined KPIRoot score remain accurate.
- The Pod Kill scenario is a boundary case: the processed service-level matrix merges replacement Pods, so Pod identity loss is partly hidden.
- The primary evidence should focus on the two CPU stress scenarios, where KPIRoot naturally matches aggregate CPU alarms to service CPU root causes.

## Re-run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\FinalProject\scripts\run-phase4-kpiroot.ps1
```

## Verification

```powershell
.\FinalProject\.conda\python.exe -m pytest .\FinalProject\tests\kpiroot -v -o "cache_dir=FinalProject\.pytest_cache"
```
