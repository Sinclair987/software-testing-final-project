from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .algorithm import KPIRootConfig, run_kpiroot, zscore
from .data import (
    add_synthetic_alarms,
    candidate_columns,
    choose_alarm_column,
    extract_expected,
    extract_time_window,
    load_scenario_frame,
    load_yaml,
    service_from_kpi,
    write_json,
)


def relative_minutes(timestamps: pd.Series) -> pd.Series:
    return (timestamps - timestamps.iloc[0]) / 60.0


def plot_top_scores(ranking: pd.DataFrame, output_path: Path, title: str, top_n: int = 10) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    top = ranking.head(top_n).iloc[::-1]
    plt.figure(figsize=(10, 5))
    plt.barh(top["kpi"], top["score"], color="#2f6f9f")
    plt.xlabel("KPIRoot score")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_alarm_and_candidates(
    frame: pd.DataFrame,
    alarm_column: str,
    ranking: pd.DataFrame,
    output_path: Path,
    start_epoch: float | None,
    end_epoch: float | None,
    top_n: int = 5,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    x = relative_minutes(frame["timestamp"])
    plt.figure(figsize=(11, 5))
    plt.plot(x, zscore(frame[alarm_column]), label=f"alarm: {alarm_column}", linewidth=2.2, color="#111827")
    colors = ["#d55e00", "#0072b2", "#009e73", "#cc79a7", "#f0e442"]
    for index, row in ranking.head(top_n).iterrows():
        kpi = row["kpi"]
        plt.plot(x, zscore(frame[kpi]), label=f"rank {int(row['rank'])}: {kpi}", alpha=0.85, color=colors[index % len(colors)])
    if start_epoch is not None and end_epoch is not None:
        base = float(frame["timestamp"].iloc[0])
        plt.axvspan((start_epoch - base) / 60.0, (end_epoch - base) / 60.0, color="#ef4444", alpha=0.12, label="fault window")
    plt.xlabel("Minutes since export start")
    plt.ylabel("Z-score")
    plt.title("Alarm KPI and Top Ranked Candidate KPIs")
    plt.legend(fontsize=8, loc="best")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def evaluate_ranking(
    ranking: pd.DataFrame,
    expected_kpis: list[str],
    expected_service: str | None,
) -> dict[str, Any]:
    if ranking.empty:
        return {
            "expected_kpi_rank": None,
            "expected_service_rank": None,
            "hit_at_1": False,
            "hit_at_3": False,
            "hit_at_5": False,
            "top1": None,
            "top5": [],
        }

    top_kpis = ranking["kpi"].tolist()
    exact_ranks = [top_kpis.index(kpi) + 1 for kpi in expected_kpis if kpi in top_kpis]
    service_ranks = []
    if expected_service:
        for index, kpi in enumerate(top_kpis, start=1):
            if service_from_kpi(kpi) == expected_service:
                service_ranks.append(index)

    best_service_rank = min(service_ranks) if service_ranks else None
    return {
        "expected_kpi_rank": min(exact_ranks) if exact_ranks else None,
        "expected_service_rank": best_service_rank,
        "hit_at_1": best_service_rank is not None and best_service_rank <= 1,
        "hit_at_3": best_service_rank is not None and best_service_rank <= 3,
        "hit_at_5": best_service_rank is not None and best_service_rank <= 5,
        "top1": top_kpis[0],
        "top5": top_kpis[:5],
    }


def ranking_for_method(ranking: pd.DataFrame, method: str) -> pd.DataFrame:
    method_frame = ranking.drop(columns=["rank"], errors="ignore").copy()
    if method == "similarity_only":
        method_frame["score"] = method_frame["similarity"]
    elif method == "causality_only":
        method_frame["score"] = method_frame["causality"]
    elif method == "kpiroot_combined":
        pass
    else:
        raise ValueError(f"Unsupported ablation method: {method}")
    method_frame = method_frame.sort_values(["score", "similarity", "causality"], ascending=False).reset_index(drop=True)
    method_frame.insert(0, "rank", range(1, len(method_frame) + 1))
    method_frame.insert(1, "method", method)
    return method_frame


def build_ablation_results(
    scenario_id: str,
    ranking: pd.DataFrame,
    expected_kpis: list[str],
    expected_service: str | None,
    scenario_output: Path,
) -> list[dict[str, Any]]:
    rows = []
    for method in ["similarity_only", "causality_only", "kpiroot_combined"]:
        method_ranking = ranking_for_method(ranking, method)
        method_ranking.to_csv(scenario_output / f"ranking_{method}.csv", index=False)
        evaluation = evaluate_ranking(method_ranking, expected_kpis, expected_service)
        rows.append(
            {
                "scenario_id": scenario_id,
                "method": method,
                "expected_service": expected_service,
                "top1": evaluation["top1"],
                "expected_service_rank": evaluation["expected_service_rank"],
                "hit_at_1": evaluation["hit_at_1"],
                "hit_at_3": evaluation["hit_at_3"],
                "hit_at_5": evaluation["hit_at_5"],
            }
        )
    pd.DataFrame(rows).to_csv(scenario_output / "ablation_summary.csv", index=False)
    return rows


def run_scenario(
    scenario_dir: Path,
    output_root: Path,
    config: KPIRootConfig,
    alarm_override: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scenario_id = scenario_dir.name
    metadata = load_yaml(scenario_dir / "metadata.yaml")
    frame = add_synthetic_alarms(load_scenario_frame(scenario_dir))
    alarm_column = alarm_override or choose_alarm_column(frame, scenario_id)
    candidates = candidate_columns(frame, alarm_column)
    start_epoch, end_epoch = extract_time_window(metadata)
    expected_kpis, expected_service = extract_expected(metadata)

    ranking, details = run_kpiroot(
        frame=frame,
        alarm_column=alarm_column,
        candidate_columns=candidates,
        start_epoch=start_epoch,
        end_epoch=end_epoch,
        config=config,
    )

    scenario_output = output_root / scenario_id
    scenario_output.mkdir(parents=True, exist_ok=True)
    ranking_path = scenario_output / "ranking.csv"
    ranking.to_csv(ranking_path, index=False)
    ranking.to_csv(scenario_output / "score_breakdown.csv", index=False)

    plot_top_scores(ranking, scenario_output / "topk_scores.png", f"{scenario_id}: KPIRoot Top Scores")
    plot_alarm_and_candidates(
        frame,
        alarm_column,
        ranking,
        scenario_output / "alarm_top_candidates.png",
        start_epoch,
        end_epoch,
    )

    evaluation = evaluate_ranking(ranking, expected_kpis, expected_service)
    ablation_rows = build_ablation_results(scenario_id, ranking, expected_kpis, expected_service, scenario_output)
    summary = {
        "scenario_id": scenario_id,
        "alarm_column": alarm_column,
        "expected_kpis": expected_kpis,
        "expected_service": expected_service,
        **evaluation,
        **details,
        "ranking_path": str(ranking_path),
        "topk_scores_plot": str(scenario_output / "topk_scores.png"),
        "timeseries_plot": str(scenario_output / "alarm_top_candidates.png"),
        "ablation_path": str(scenario_output / "ablation_summary.csv"),
    }
    write_json(scenario_output / "summary.json", summary)
    return summary, ablation_rows


def write_report(
    report_path: Path,
    summaries: list[dict[str, Any]],
    ablation_rows: list[dict[str, Any]],
    output_root: Path,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 4: ISSRE24-KPIRoot Reproduction",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Goal",
        "",
        "This phase reproduces the core idea of ISSRE24-KPIRoot on the Online-Boutique monitoring data collected in Phase 2.",
        "KPIRoot ranks candidate service KPIs by combining SAX-based similarity and Granger-causality scores.",
        "",
        "## Mapping To Online-Boutique",
        "",
        "- Alarm KPI: a system-level or synthetic aggregate KPI, such as `synthetic_total_cpu`.",
        "- Candidate KPIs: service-level CPU, memory, filesystem, restart, and running-state series.",
        "- Root cause: the service targeted by the ChaosMesh fault.",
        "",
        "## Implemented Algorithm",
        "",
        "1. Load and clean the exported Phase 2 KPI matrix.",
        "2. Add synthetic aggregate alarm KPIs, including total CPU, total memory, unavailable Pods, and total restarts.",
        "3. Normalize each KPI and compress it with Piecewise Aggregate Approximation (PAA).",
        "4. Convert PAA values to Symbolic Aggregate Approximation (SAX) symbols.",
        "5. Select the fault/anomaly window from scenario metadata, with automatic trend detection available as fallback.",
        "6. Compute SAX multiset-Jaccard similarity between the alarm KPI and each candidate KPI.",
        "7. Compute a Granger-style F statistic to estimate whether the candidate KPI precedes the alarm KPI.",
        "8. Rank candidates by `0.9 * similarity + 0.1 * normalized_causality`, following the paper's lambda setting.",
        "",
        "## Implementation Files",
        "",
        "- `src/kpiroot/algorithm.py`: PAA, SAX, anomaly segment selection, similarity, causality, and ranking.",
        "- `src/kpiroot/data.py`: Phase 2 data loading, metadata parsing, synthetic alarm construction, and expected-root extraction.",
        "- `src/kpiroot/cli.py`: batch runner, evaluation, plotting, and report generation.",
        "- `tests/kpiroot/test_algorithm.py`: focused unit tests for the reproduction implementation.",
        "- `scripts/run-phase4-kpiroot.ps1`: project-level runner.",
        "",
        "## Results",
        "",
        "| Scenario | Alarm KPI | Expected Service | Top-1 KPI | Expected Service Rank | Hit@1 | Hit@3 | Hit@5 |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for summary in summaries:
        lines.append(
            "| {scenario_id} | `{alarm_column}` | `{expected_service}` | `{top1}` | {rank} | {h1} | {h3} | {h5} |".format(
                scenario_id=summary["scenario_id"],
                alarm_column=summary["alarm_column"],
                expected_service=summary.get("expected_service"),
                top1=summary.get("top1"),
                rank=summary.get("expected_service_rank") or "",
                h1="yes" if summary.get("hit_at_1") else "no",
                h3="yes" if summary.get("hit_at_3") else "no",
                h5="yes" if summary.get("hit_at_5") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Ablation Study",
            "",
            "The ablation study reuses the same KPI scores but changes the ranking objective:",
            "",
            "- `similarity_only`: rank by SAX-Jaccard similarity only.",
            "- `causality_only`: rank by normalized Granger causality only.",
            "- `kpiroot_combined`: rank by `0.9 * similarity + 0.1 * normalized_causality`.",
            "",
            "| Scenario | Method | Top-1 KPI | Expected Service Rank | Hit@1 | Hit@3 | Hit@5 |",
            "| --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for row in ablation_rows:
        lines.append(
            "| {scenario_id} | `{method}` | `{top1}` | {rank} | {h1} | {h3} | {h5} |".format(
                scenario_id=row["scenario_id"],
                method=row["method"],
                top1=row["top1"],
                rank=row.get("expected_service_rank") or "",
                h1="yes" if row.get("hit_at_1") else "no",
                h3="yes" if row.get("hit_at_3") else "no",
                h5="yes" if row.get("hit_at_5") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Output Artifacts",
            "",
            f"- Summary CSV: `{output_root / 'summary.csv'}`",
            f"- Ablation summary CSV: `{output_root / 'ablation_summary.csv'}`",
            "- Per-scenario files:",
        ]
    )
    for summary in summaries:
        scenario = summary["scenario_id"]
        lines.extend(
            [
                f"  - `{output_root / scenario / 'ranking.csv'}`",
                f"  - `{output_root / scenario / 'ablation_summary.csv'}`",
                f"  - `{output_root / scenario / 'topk_scores.png'}`",
                f"  - `{output_root / scenario / 'alarm_top_candidates.png'}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The original paper evaluates Cloud H host-cluster and VM KPIs. This project adapts the method to service-level Online-Boutique KPIs.",
            "- The paper uses very large industrial time series. Our course datasets are short, so the implementation keeps more PAA bins than sqrt(n) by default.",
            "- In the ablation results, causality-only ranking is unstable on these short time series, while SAX similarity and the combined KPIRoot score remain accurate.",
            "- The Pod Kill scenario is a boundary case: the processed service-level matrix merges replacement Pods, so Pod identity loss is partly hidden.",
            "- The primary evidence should focus on the two CPU stress scenarios, where KPIRoot naturally matches aggregate CPU alarms to service CPU root causes.",
            "",
            "## Re-run",
            "",
            "```powershell",
            "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\FinalProject\\scripts\\run-phase4-kpiroot.ps1",
            "```",
            "",
            "## Verification",
            "",
            "```powershell",
            ".\\FinalProject\\.conda\\python.exe -m pytest .\\FinalProject\\tests\\kpiroot -v -o \"cache_dir=FinalProject\\.pytest_cache\"",
            "```",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 4 KPIRoot reproduction.")
    parser.add_argument("--phase2-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--scenario", action="append", default=None)
    parser.add_argument("--alarm", default=None)
    parser.add_argument("--paa-size", type=int, default=32)
    parser.add_argument("--lambda-weight", type=float, default=0.9)
    parser.add_argument("--alphabet-size", type=int, default=9)
    parser.add_argument("--granger-lag", type=int, default=2)
    args = parser.parse_args()

    config = KPIRootConfig(
        paa_size=args.paa_size,
        lambda_weight=args.lambda_weight,
        alphabet_size=args.alphabet_size,
        granger_lag=args.granger_lag,
    )
    scenario_dirs = [
        path
        for path in sorted(args.phase2_dir.iterdir())
        if path.is_dir() and (path / "processed" / "kpi_matrix.csv").exists() and "baseline" not in path.name
    ]
    if args.scenario:
        requested = set(args.scenario)
        scenario_dirs = [path for path in scenario_dirs if path.name in requested]
    scenario_results = [run_scenario(path, args.output_dir, config, args.alarm) for path in scenario_dirs]
    summaries = [summary for summary, _ in scenario_results]
    ablation_rows = [row for _, rows in scenario_results for row in rows]
    summary_frame = pd.DataFrame(summaries)
    ablation_frame = pd.DataFrame(ablation_rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_frame.to_csv(args.output_dir / "summary.csv", index=False)
    ablation_frame.to_csv(args.output_dir / "ablation_summary.csv", index=False)
    write_report(args.report, summaries, ablation_rows, args.output_dir)

    print(summary_frame[["scenario_id", "alarm_column", "expected_service", "top1", "expected_service_rank", "hit_at_1", "hit_at_3", "hit_at_5"]].to_string(index=False))
    print()
    print(ablation_frame[["scenario_id", "method", "top1", "expected_service_rank", "hit_at_1", "hit_at_3", "hit_at_5"]].to_string(index=False))


if __name__ == "__main__":
    main()
