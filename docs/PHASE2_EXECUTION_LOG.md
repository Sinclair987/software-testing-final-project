# Phase 2 Execution Log

Date: 2026-06-05

## Completed by Codex

### Cluster Verification

Verified that the following namespaces are healthy:

- `online-boutique`
- `monitoring`
- `chaos-testing`

Online-Boutique currently has 12 Pods running.

Prometheus/Grafana are running in `monitoring`.

ChaosMesh is running in `chaos-testing`.

### Prometheus Metric Verification

Verified that Prometheus can query Online-Boutique metrics:

- `container_cpu_usage_seconds_total{namespace="online-boutique"}` returns 12 series.
- `container_memory_working_set_bytes{namespace="online-boutique"}` returns 12 series.
- `kube_pod_container_status_restarts_total{namespace="online-boutique"}` returns restart metrics for all service containers.

### Frontend Blackbox Probe

Deployed `blackbox-exporter` in the `monitoring` namespace.

Created files:

- `FinalProject/monitoring/blackbox-exporter.yaml`
- `FinalProject/scripts/enable-blackbox-frontend-probe.ps1`

Patched Prometheus with a scrape job:

```text
online-boutique-frontend-blackbox
```

Verified:

```text
probe_success{job="online-boutique-frontend-blackbox"} = 1
```

This gives KPIRoot a suitable frontend service-quality alarm KPI.

### ChaosMesh Fault Definitions

Created reusable ChaosMesh YAML files:

- `FinalProject/chaos/pod-kill-paymentservice.yaml`
- `FinalProject/chaos/stress-paymentservice-cpu.yaml`
- `FinalProject/chaos/stress-frontend-cpu.yaml`
- `FinalProject/chaos/network-delay-checkoutservice.yaml`

Validated all YAML files with:

```powershell
kubectl apply --dry-run=client -f .\FinalProject\chaos
```

No ChaosMesh fault was actually injected yet.

Verified no active chaos objects remain:

```text
No resources found in online-boutique namespace.
```

### Grafana Dashboard Artifact

Created:

```text
FinalProject/grafana/online-boutique-maintenance-dashboard.json
```

This dashboard includes panels for:

- CPU by Pod
- memory by Pod
- container restarts
- Pod running status
- frontend probe duration
- frontend probe success
- filesystem reads
- filesystem writes

Attempted automatic import through Grafana API, but Grafana rejected the default lab2 credential:

```text
401 Unauthorized: invalid username or password
```

Therefore, dashboard import requires the user's Grafana password.

Update on 2026-06-05:

- Rebuilt the dashboard JSON for Grafana `v7.5.5` compatibility.
- Replaced newer `timeseries` panels with legacy `graph` panels.
- Updated Grafana `Prometheus` datasource from stale `direct` URL
  `http://127.0.0.1:8792` to cluster-internal proxy URL
  `http://prometheus.monitoring.svc.cluster.local:9090`.
- Re-imported the dashboard through Grafana API.
- Verified Grafana datasource proxy query returned 12 Online-Boutique CPU
  series.

### Data Export Script and Baseline Data

Created:

```text
FinalProject/scripts/export-prometheus-range.py
```

Exported a normal baseline sample:

```text
FinalProject/data/phase2/baseline-sample/
```

Important files:

- `metadata.yaml`
- `prometheus_raw/*.csv`
- `processed/kpi_matrix.csv`
- `processed/series_labels.json`

The processed matrix currently has:

```text
rows: 14
columns: 60
```

This is a small connectivity sample, not the final experiment dataset.

## User Actions Still Required

## First Fault Experiment Completed

Experiment:

```text
stress-paymentservice-cpu-001
```

Evidence and data were organized under:

```text
FinalProject/data/phase2/stress-paymentservice-cpu-001/
```

The screenshots were moved from `FinalProject/screenshot` to:

```text
FinalProject/data/phase2/stress-paymentservice-cpu-001/screenshots/
```

Data was exported for:

```text
2026-06-05T01:50:00+08:00 -> 2026-06-05T02:18:30+08:00
```

Processed matrix:

```text
FinalProject/data/phase2/stress-paymentservice-cpu-001/processed/kpi_matrix.csv
```

Data check:

- rows: 115
- columns: 62
- `cpu__paymentservice` baseline average: about `0.00064`
- `cpu__paymentservice` fault-window average: about `0.16999`
- `cpu__paymentservice` fault-window max: about `0.20016`
- `alarm_frontend_probe_success` stayed at `1.0`

Conclusion:

```text
The StressChaos experiment was successful. The injected CPU stress produced a
clear paymentservice CPU anomaly and is suitable for the later KPIRoot
reproduction.
```

### 1. Import or Open the Grafana Dashboard

Run Grafana port-forward:

```powershell
cd D:\Study\SoftwareTesting
kubectl port-forward -n monitoring service/grafana 3000:80
```

Open:

```text
http://127.0.0.1:3000
```

Log in with your actual Grafana password.

Then import:

```text
FinalProject/grafana/online-boutique-maintenance-dashboard.json
```

Alternative: if you know the password, run:

```powershell
.\FinalProject\scripts\import-grafana-dashboard.ps1 -Password "<your-grafana-password>"
```

### 2. Take Required Screenshots

Capture these for the report:

- `kubectl get pods -n online-boutique`
- `kubectl get all -n monitoring`
- `kubectl get all -n chaos-testing`
- Prometheus targets page
- Prometheus query for Online-Boutique CPU or memory
- Prometheus query for `probe_success`
- Grafana dashboard during normal baseline

### 3. Run Fault Experiments

For each experiment:

1. Record baseline start time.
2. Observe Grafana for about 10 minutes.
3. Apply one ChaosMesh YAML.
4. Record fault start time.
5. Observe Grafana during the 5-minute fault.
6. Record fault end time.
7. Observe recovery for about 10 minutes.
8. Export Prometheus data for the full window.
9. Save screenshots and fill metadata.

Recommended first experiment:

```powershell
kubectl apply -f .\FinalProject\chaos\stress-paymentservice-cpu.yaml
```

After it ends, confirm no active chaos object remains:

```powershell
kubectl get podchaos,stresschaos,networkchaos -n online-boutique
```

Clean up if needed:

```powershell
kubectl delete podchaos --all -n online-boutique --ignore-not-found
kubectl delete stresschaos --all -n online-boutique --ignore-not-found
kubectl delete networkchaos --all -n online-boutique --ignore-not-found
```

### 4. Export Fault Data

Keep Prometheus port-forward running:

```powershell
kubectl port-forward -n monitoring service/prometheus 9090:9090
```

Then export:

```powershell
.\FinalProject\.conda\python.exe .\FinalProject\scripts\export-prometheus-range.py `
  --prometheus-url http://127.0.0.1:9090 `
  --start "YYYY-MM-DDTHH:mm:ss+08:00" `
  --end "YYYY-MM-DDTHH:mm:ss+08:00" `
  --step 15 `
  --output .\FinalProject\data\phase2\stress-paymentservice-cpu-001
```

Fill:

```text
FinalProject/data/phase2/metadata-template.yaml
```

and save it as:

```text
FinalProject/data/phase2/<scenario_id>/metadata.yaml
```

### 5. Prepare for KPIRoot

For each fault dataset, the key file for Phase 4 is:

```text
processed/kpi_matrix.csv
```

The likely alarm KPIs are:

- `alarm_frontend_probe_duration`
- `alarm_frontend_probe_success`

The expected root-cause KPI should match the injected service, for example:

```text
cpu__paymentservice
```

for `stress-paymentservice-cpu.yaml`.

## Completed Fault Dataset: pod-kill-paymentservice-001

Status: completed and validated.

The second fault experiment used:

```powershell
kubectl apply -f .\FinalProject\chaos\pod-kill-paymentservice.yaml
```

Observed timeline:

- Baseline start: `2026-06-05T02:45:55.5019669+08:00`
- Fault apply time: `2026-06-05T02:51:15.6821586+08:00`
- Chaos creation time: `2026-06-05T02:51:17+08:00`
- Fault confirmed time: `2026-06-05T02:51:25.1436113+08:00`
- Recovery and cleanup confirmed: `2026-06-05T02:59:47.6511894+08:00`
- Export window: `2026-06-05T02:45:55+08:00` to `2026-06-05T03:02:30+08:00`

Validation result:

- `paymentservice-85698c8c59-sss44` was replaced by `paymentservice-85698c8c59-5sx8h`.
- All Online-Boutique Pods returned to `Running`.
- No ChaosMesh objects remained in the `online-boutique` namespace after cleanup.
- `alarm_frontend_probe_success` remained `1` throughout the export window.
- `processed/kpi_matrix.csv` contains 67 rows and 62 columns.

Note: this fault is expected to look less dramatic than CPU stress on the overall Grafana dashboard. PodKill creates a replacement Pod, so the container restart counter can remain `0`; the strongest evidence is the old paymentservice Pod series ending and the replacement paymentservice Pod series appearing.

## Completed Fault Dataset: stress-frontend-cpu-001

Status: completed and validated.

The third fault experiment used:

```powershell
kubectl apply -f .\FinalProject\chaos\stress-frontend-cpu.yaml
```

Observed timeline:

- Baseline start: `2026-06-05T03:14:44.9566104+08:00`
- Fault apply time: `2026-06-05T03:20:10.5531737+08:00`
- Chaos creation time: `2026-06-05T03:20:10+08:00`
- Fault confirmed time: `2026-06-05T03:20:10.8167056+08:00`
- Estimated fault end: `2026-06-05T03:25:10+08:00`
- Recovery and cleanup confirmed: `2026-06-05T03:31:06.2251035+08:00`
- Export window: `2026-06-05T03:14:44+08:00` to `2026-06-05T03:31:30+08:00`

Validation result:

- `cpu__frontend` baseline average: about `0.016`.
- `cpu__frontend` fault-window average: about `0.170`.
- `cpu__frontend` fault-window max: about `0.200`.
- `alarm_frontend_probe_duration` increased during the fault, with max about `0.225s`.
- `alarm_frontend_probe_success` remained `1`.
- `running__frontend` remained `1`.
- No ChaosMesh objects remained in the `online-boutique` namespace after cleanup.
- `processed/kpi_matrix.csv` contains 68 rows and 60 columns.
