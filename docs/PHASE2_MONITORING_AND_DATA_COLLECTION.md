# Phase 2: Prometheus, Grafana, ChaosMesh, and KPI Data Collection

This document describes the concrete Phase 2 workflow for the final project.
The target microservice system is `JoinFyc/Online-Boutique` deployed in the
`online-boutique` namespace.

## 1. What Phase 2 Must Achieve

According to the final project requirement, Phase 2 is not only "open
Prometheus and Grafana". It must produce monitoring evidence and usable data
for the later paper reproduction stage.

Required outcomes:

- Prometheus can scrape monitoring data from the Kubernetes cluster and the
  Online-Boutique workload.
- Grafana can visualize the collected metrics.
- ChaosMesh can inject faults into Online-Boutique.
- Prometheus/Grafana can show metric changes before, during, and after faults.
- The monitoring data can later be exported and transformed into time series
  input for the KPIRoot reproduction.

The lab2 workflow is still useful, but SockShop is replaced by
Online-Boutique.

## 2. Relation to ISSRE24-KPIRoot

KPIRoot localizes root-cause KPIs from monitoring time series.

In the original paper:

- There is one alarm KPI, such as the overall service quality or host-cluster
  overload metric.
- There are many underlying KPIs, such as CPU, memory, I/O, bandwidth, QPS,
  and error-related metrics for individual entities.
- KPIRoot first detects an anomaly segment in the alarm KPI.
- It compares each underlying KPI with the alarm KPI by SAX/Jaccard similarity.
- It also checks temporal causality with Granger causality.
- It ranks KPIs by a combined score. The top-ranked KPIs are treated as root
  causes.

In our project, the mapping is:

- Alarm KPI: frontend service quality, preferably `probe_duration_seconds` or
  `probe_success` from a blackbox probe. If blackbox probing is not added yet,
  use frontend CPU/memory as a temporary alarm KPI.
- Underlying KPIs: per-service CPU, memory, filesystem I/O, restart count, and
  Pod running status from Prometheus.
- Ground truth: the service and metric targeted by ChaosMesh, for example
  `paymentservice` CPU stress means the expected root-cause KPI is
  `paymentservice_cpu`.

This means Phase 2 must record fault metadata carefully: target service, fault
type, injection start time, injection end time, recovery time, and the expected
root-cause KPI.

## 3. Current Cluster Status

Checked on 2026-06-05:

- `online-boutique`: 12 Online-Boutique Pods are running.
- `monitoring`: lab2 Prometheus/Grafana stack is still running.
- `chaos-testing`: ChaosMesh is still running.
- Prometheus scrape interval is currently 15 seconds.
- Prometheus already scrapes:
  - `kubernetes-cadvisor`
  - `kube-state-metrics`
  - `node-exporter`
  - Kubernetes API/node metrics
- Prometheus has confirmed Online-Boutique metrics:
  - `container_cpu_usage_seconds_total{namespace="online-boutique"}`
  - `container_memory_working_set_bytes{namespace="online-boutique"}`
  - `kube_pod_status_phase{namespace="online-boutique"}`
  - `kube_pod_container_status_restarts_total{namespace="online-boutique"}`

So we can reuse the existing lab2 monitoring namespace instead of reinstalling
Prometheus/Grafana.

## 4. Preparation Before Each Phase 2 Run

Start Docker Desktop first. Then open PowerShell:

```powershell
cd D:\Study\SoftwareTesting
minikube start
```

Recover Online-Boutique if needed:

```powershell
.\FinalProject\scripts\resume-online-boutique.ps1 -NoPortForward
```

Check all required namespaces:

```powershell
kubectl get pods -n online-boutique
kubectl get all -n monitoring
kubectl get all -n chaos-testing
```

Expected:

- Online-Boutique Pods should be `Running`.
- Prometheus and Grafana Pods should be `Running`.
- ChaosMesh controller, daemon, dashboard, and DNS server should be `Running`.

## 5. Open Prometheus, Grafana, and ChaosMesh

### 5.1 Prometheus

Option A, use Minikube NodePort URL:

```powershell
minikube service prometheus -n monitoring --url
```

Open the printed URL in a browser.

Option B, use stable local port forwarding:

```powershell
kubectl port-forward -n monitoring service/prometheus 9090:9090
```

Open:

```text
http://127.0.0.1:9090
```

### 5.2 Grafana

Option A:

```powershell
minikube service grafana -n monitoring --url
```

Option B:

```powershell
kubectl port-forward -n monitoring service/grafana 3000:80
```

Open:

```text
http://127.0.0.1:3000
```

Default lab2 login is usually:

```text
username: admin
password: admin
```

If Grafana asks for a new password, set one and record it in private notes.
Do not commit passwords to GitHub.

### 5.3 ChaosMesh Dashboard

```powershell
kubectl port-forward -n chaos-testing service/chaos-dashboard 2333:2333
```

Open:

```text
http://127.0.0.1:2333
```

If it asks for a token, use the dashboard prompt to generate a Manager token.
Use cluster-scoped Manager role as in lab2.

## 6. Verify Prometheus Data

Open Prometheus and run these PromQL queries.

Check scrape targets:

```promql
up
```

Check Online-Boutique CPU metrics:

```promql
sum by (pod) (
  rate(container_cpu_usage_seconds_total{namespace="online-boutique"}[1m])
)
```

Check memory:

```promql
sum by (pod) (
  container_memory_working_set_bytes{namespace="online-boutique"}
)
```

Check restart counts:

```promql
sum by (pod, container) (
  kube_pod_container_status_restarts_total{namespace="online-boutique"}
)
```

Check running status:

```promql
kube_pod_status_phase{namespace="online-boutique", phase="Running"}
```

Check filesystem reads/writes if needed:

```promql
sum by (pod) (
  rate(container_fs_reads_bytes_total{namespace="online-boutique"}[1m])
)
```

```promql
sum by (pod) (
  rate(container_fs_writes_bytes_total{namespace="online-boutique"}[1m])
)
```

For the report, capture:

- Prometheus `Status -> Targets`.
- At least one query result showing Online-Boutique metrics.
- Query graphs before and after a fault.

## 7. Configure Grafana

### 7.1 Add Prometheus Data Source

In Grafana:

1. Open `Connections` or `Data sources`.
2. Add `Prometheus`.
3. Use this URL:

```text
http://prometheus.monitoring.svc.cluster.local:9090
```

Because Grafana runs inside the cluster, this in-cluster service address is
more reliable than a local `127.0.0.1` address.

4. Click `Save & Test`.

Expected result:

```text
Successfully queried the Prometheus API
```

### 7.2 Create Dashboard Panels

Create a dashboard named:

```text
Online-Boutique Maintenance Dashboard
```

Add these panels.

Panel 1, CPU usage by Pod:

```promql
sum by (pod) (
  rate(container_cpu_usage_seconds_total{namespace="online-boutique"}[1m])
)
```

Panel 2, memory working set by Pod:

```promql
sum by (pod) (
  container_memory_working_set_bytes{namespace="online-boutique"}
)
```

Panel 3, restart count:

```promql
sum by (pod, container) (
  kube_pod_container_status_restarts_total{namespace="online-boutique"}
)
```

Panel 4, Pod running status:

```promql
kube_pod_status_phase{namespace="online-boutique", phase="Running"}
```

Panel 5, filesystem writes:

```promql
sum by (pod) (
  rate(container_fs_writes_bytes_total{namespace="online-boutique"}[1m])
)
```

Panel 6, filesystem reads:

```promql
sum by (pod) (
  rate(container_fs_reads_bytes_total{namespace="online-boutique"}[1m])
)
```

For each panel, use a time range such as:

```text
Last 30 minutes
```

During fault injection, use:

```text
Last 15 minutes
```

Export the dashboard JSON and save it later under:

```text
FinalProject/grafana/online-boutique-maintenance-dashboard.json
```

## 8. Recommended Add-on: Frontend Service Quality Probe

KPIRoot works best when there is an alarm KPI representing service quality.
Current lab2 Prometheus already has resource and Kubernetes metrics, but it
does not directly provide frontend HTTP latency/error metrics.

Recommended solution: deploy a Prometheus blackbox exporter and probe the
frontend service. This gives:

- `probe_success`
- `probe_duration_seconds`

These are much better alarm KPIs for KPIRoot than raw CPU or memory.

If time is tight, this add-on can be skipped temporarily. In that case, use
frontend CPU or memory as a simplified alarm KPI, and explain the limitation in
the report.

Suggested blackbox workflow:

1. Deploy `blackbox-exporter` into `monitoring`.
2. Configure Prometheus to scrape:

```text
http://frontend.online-boutique.svc.cluster.local
```

3. Verify:

```promql
probe_success
probe_duration_seconds
```

4. Add Grafana panels for frontend success and response duration.

We should implement this add-on in a later execution step, because it requires
editing the Prometheus ConfigMap and restarting the Prometheus deployment.

## 9. Fault Injection Design

Use at least three fault scenarios. Each scenario should have:

- a clear target service
- a clear expected root-cause KPI
- a normal period
- a fault period
- a recovery period
- saved ChaosMesh YAML
- saved Prometheus/Grafana screenshots
- exported Prometheus time series

Recommended timing for each scenario:

```text
normal baseline: 10 minutes
fault injection: 5 minutes
recovery: 10 minutes
total: about 25 minutes
```

Prometheus scrape interval is 15 seconds, so 25 minutes gives about 100 samples.
This is enough for a classroom KPIRoot reproduction. If time allows, use 40 to
60 minutes for cleaner Granger causality results.

## 10. Scenario A: Pod Kill

Purpose:

- Reproduce the basic lab2 ChaosMesh fault.
- Show Pod restart and service recovery.

Create:

```text
FinalProject/chaos/pod-kill-paymentservice.yaml
```

YAML:

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill-paymentservice
  namespace: online-boutique
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - online-boutique
    labelSelectors:
      app: paymentservice
```

Run:

```powershell
kubectl apply -f .\FinalProject\chaos\pod-kill-paymentservice.yaml
```

Check:

```powershell
kubectl get podchaos -n online-boutique
kubectl get pods -n online-boutique -w
```

Delete after completion if it remains:

```powershell
kubectl delete podchaos pod-kill-paymentservice -n online-boutique --ignore-not-found
```

Expected useful KPIs:

- `kube_pod_container_status_restarts_total` for `paymentservice`
- `kube_pod_status_phase` for `paymentservice`
- frontend `probe_success` or frontend CPU/memory

Ground truth for KPIRoot:

```text
paymentservice_restart
paymentservice_running_status
```

## 11. Scenario B: CPU Stress

Purpose:

- Create a sustained metric anomaly that is easier for KPIRoot to rank.
- This is better than a one-time Pod kill for time-series RCA.

Create:

```text
FinalProject/chaos/stress-paymentservice-cpu.yaml
```

YAML:

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: stress-paymentservice-cpu
  namespace: online-boutique
spec:
  mode: one
  selector:
    namespaces:
      - online-boutique
    labelSelectors:
      app: paymentservice
  stressors:
    cpu:
      workers: 1
      load: 80
  duration: "5m"
```

Run:

```powershell
kubectl apply -f .\FinalProject\chaos\stress-paymentservice-cpu.yaml
```

Check:

```powershell
kubectl get stresschaos -n online-boutique
kubectl describe stresschaos stress-paymentservice-cpu -n online-boutique
```

Delete if needed:

```powershell
kubectl delete stresschaos stress-paymentservice-cpu -n online-boutique --ignore-not-found
```

Expected useful KPIs:

- `paymentservice` CPU rises during the fault.
- frontend latency or service quality may degrade if the target affects request
  flow.
- other services may show secondary effects later.

Ground truth for KPIRoot:

```text
paymentservice_cpu
```

## 12. Scenario C: Frontend CPU Stress

Purpose:

- Create an obvious service-quality anomaly near the system entry point.
- Good for report screenshots because frontend is user-facing.

Create:

```text
FinalProject/chaos/stress-frontend-cpu.yaml
```

YAML:

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: stress-frontend-cpu
  namespace: online-boutique
spec:
  mode: one
  selector:
    namespaces:
      - online-boutique
    labelSelectors:
      app: frontend
  stressors:
    cpu:
      workers: 1
      load: 80
  duration: "5m"
```

Run:

```powershell
kubectl apply -f .\FinalProject\chaos\stress-frontend-cpu.yaml
```

Delete if needed:

```powershell
kubectl delete stresschaos stress-frontend-cpu -n online-boutique --ignore-not-found
```

Expected useful KPIs:

- `frontend` CPU rises.
- frontend `probe_duration_seconds` rises if blackbox probing is enabled.
- frontend `probe_success` may drop if the service becomes too slow.

Ground truth for KPIRoot:

```text
frontend_cpu
```

## 13. Optional Scenario D: Network Delay

Purpose:

- Create a latency-related anomaly.
- Useful if blackbox frontend latency is enabled.

Create:

```text
FinalProject/chaos/network-delay-checkoutservice.yaml
```

YAML:

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay-checkoutservice
  namespace: online-boutique
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - online-boutique
    labelSelectors:
      app: checkoutservice
  delay:
    latency: "300ms"
    correlation: "100"
    jitter: "0ms"
  duration: "5m"
```

Run:

```powershell
kubectl apply -f .\FinalProject\chaos\network-delay-checkoutservice.yaml
```

Delete if needed:

```powershell
kubectl delete networkchaos network-delay-checkoutservice -n online-boutique --ignore-not-found
```

Ground truth for KPIRoot:

```text
checkoutservice_network_delay
```

## 14. Data Collection Protocol

For each fault scenario, create a directory:

```text
FinalProject/data/phase2/<scenario_id>/
```

Example:

```text
FinalProject/data/phase2/stress-paymentservice-cpu-001/
```

Inside it, save:

```text
metadata.yaml
prometheus_raw/
processed/
screenshots/
```

Example `metadata.yaml`:

```yaml
scenario_id: stress-paymentservice-cpu-001
date: 2026-06-05
system: Online-Boutique
namespace: online-boutique
fault:
  tool: ChaosMesh
  kind: StressChaos
  name: stress-paymentservice-cpu
  target_app: paymentservice
  expected_root_cause_kpis:
    - paymentservice_cpu
timing:
  baseline_start: "YYYY-MM-DDTHH:mm:ss+08:00"
  fault_start: "YYYY-MM-DDTHH:mm:ss+08:00"
  fault_end: "YYYY-MM-DDTHH:mm:ss+08:00"
  recovery_end: "YYYY-MM-DDTHH:mm:ss+08:00"
prometheus:
  scrape_interval_seconds: 15
  step_seconds: 15
notes:
  - "Record observations here."
```

Record timestamps immediately before applying the ChaosMesh YAML:

```powershell
Get-Date -Format o
kubectl apply -f .\FinalProject\chaos\stress-paymentservice-cpu.yaml
Get-Date -Format o
```

After the duration ends, record:

```powershell
Get-Date -Format o
kubectl get pods -n online-boutique
```

## 15. Prometheus Queries to Export

Export these query groups for each scenario.

Alarm KPI, preferred after blackbox exporter:

```promql
probe_duration_seconds{instance=~".*frontend.*"}
```

```promql
probe_success{instance=~".*frontend.*"}
```

Temporary alarm KPI if blackbox exporter is not enabled:

```promql
sum by (pod) (
  rate(container_cpu_usage_seconds_total{namespace="online-boutique", pod=~"frontend-.*"}[1m])
)
```

Underlying CPU KPIs:

```promql
sum by (pod) (
  rate(container_cpu_usage_seconds_total{namespace="online-boutique"}[1m])
)
```

Underlying memory KPIs:

```promql
sum by (pod) (
  container_memory_working_set_bytes{namespace="online-boutique"}
)
```

Restart KPIs:

```promql
sum by (pod, container) (
  kube_pod_container_status_restarts_total{namespace="online-boutique"}
)
```

Pod running status KPIs:

```promql
kube_pod_status_phase{namespace="online-boutique", phase="Running"}
```

Filesystem I/O KPIs:

```promql
sum by (pod) (
  rate(container_fs_reads_bytes_total{namespace="online-boutique"}[1m])
)
```

```promql
sum by (pod) (
  rate(container_fs_writes_bytes_total{namespace="online-boutique"}[1m])
)
```

Use Prometheus `query_range` API:

```text
http://127.0.0.1:9090/api/v1/query_range?query=<URL_ENCODED_PROMQL>&start=<UNIX_START>&end=<UNIX_END>&step=15
```

Keep a local port-forward running while exporting:

```powershell
kubectl port-forward -n monitoring service/prometheus 9090:9090
```

Later we should add a small Python exporter script that reads `metadata.yaml`,
runs all Prometheus `query_range` calls, and writes CSV files.

## 16. Data Format for KPIRoot

The final processed dataset for each scenario should be a table:

```text
timestamp, alarm_kpi, frontend_cpu, paymentservice_cpu, cartservice_cpu, ..., paymentservice_restarts, ...
```

Rules:

- Use one row per 15 seconds.
- Align all KPIs by timestamp.
- Fill small missing gaps by interpolation or forward fill.
- Normalize each KPI before KPIRoot, as the paper does before PAA/SAX.
- Keep the original raw Prometheus JSON/CSV for traceability.
- Store the ground truth root-cause KPI in `metadata.yaml`.

For the report, show:

- the raw Prometheus data source
- the processed CSV shape
- a line chart of the alarm KPI and true root-cause KPI
- the time window used by KPIRoot

## 17. Maintenance and Recovery After Fault Injection

After each experiment:

```powershell
kubectl get pods -n online-boutique
kubectl get podchaos,stresschaos,networkchaos -n online-boutique
```

Delete remaining chaos objects:

```powershell
kubectl delete podchaos --all -n online-boutique --ignore-not-found
kubectl delete stresschaos --all -n online-boutique --ignore-not-found
kubectl delete networkchaos --all -n online-boutique --ignore-not-found
```

Wait for recovery:

```powershell
kubectl wait --for=condition=available deployment --all -n online-boutique --timeout=300s
kubectl get pods -n online-boutique
```

If the system behaves strangely:

```powershell
.\FinalProject\scripts\resume-online-boutique.ps1 -NoPortForward
```

## 18. Screenshots and Report Evidence

For Phase 2, collect these screenshots:

1. `kubectl get pods -n online-boutique`
2. `kubectl get all -n monitoring`
3. `kubectl get all -n chaos-testing`
4. Prometheus targets page
5. Prometheus query showing Online-Boutique CPU or memory
6. Grafana dashboard during normal baseline
7. ChaosMesh experiment definition or YAML
8. ChaosMesh experiment status after injection
9. Grafana dashboard during fault
10. Grafana dashboard after recovery
11. Exported data directory and metadata file

The report analysis should explicitly explain:

- which service was fault-injected
- which KPI changed first
- which KPI changed later
- how the observed trend relates to KPIRoot similarity and causality
- why the chosen ground truth KPI is reasonable

## 19. Recommended Execution Order

Use this order when actually performing Phase 2:

1. Recover Online-Boutique.
2. Verify `monitoring` and `chaos-testing`.
3. Open Prometheus, Grafana, ChaosMesh.
4. Confirm Prometheus can query Online-Boutique CPU/memory/restart metrics.
5. Create Grafana dashboard panels.
6. Optionally add blackbox frontend probing.
7. Run Scenario A, collect screenshots and data.
8. Run Scenario B, collect screenshots and data.
9. Run Scenario C, collect screenshots and data.
10. Clean all ChaosMesh experiments.
11. Verify Online-Boutique recovers.
12. Export Grafana dashboard JSON.
13. Export Prometheus time series.
14. Prepare processed CSV files for KPIRoot.

## 20. What Should Be Committed to GitHub

Commit:

- `FinalProject/chaos/*.yaml`
- `FinalProject/grafana/*.json`
- data export scripts
- KPIRoot preprocessing scripts
- selected small sample datasets
- documentation and experiment notes

Avoid committing:

- huge raw datasets
- passwords or tokens
- local logs that contain secrets

If raw data becomes large, commit a small sample and document where the full
data is stored locally.
