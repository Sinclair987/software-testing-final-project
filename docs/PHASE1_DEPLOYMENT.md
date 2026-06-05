# Phase 1 Deployment Notes

## Target System

- System: JoinFyc/Online-Boutique
- Local path: `D:\Study\SoftwareTesting\FinalProject\Online-Boutique`
- Kubernetes namespace: `online-boutique`
- Manifest used: `FinalProject\Online-Boutique\release\kubernetes-manifests.yaml`

The `kubernetes-manifests` directory is not used directly because its image names are placeholders for Skaffold. The `release` manifest contains pre-built public images.

## Deployment Commands

```powershell
minikube start
kubectl create namespace online-boutique
kubectl apply -n online-boutique -f .\FinalProject\Online-Boutique\release\kubernetes-manifests.yaml
kubectl wait --for=condition=available deployment --all -n online-boutique --timeout=300s
```

## Verification

```powershell
kubectl get pods -n online-boutique -o wide
kubectl get svc -n online-boutique -o wide
```

Expected result:

- 12 Pods are `1/1 Running`.
- `frontend-external` is exposed as a `LoadBalancer` service with a Minikube NodePort.
- On this machine, stable browser access is provided through local port forwarding.

## Local Access

Start port forwarding:

```powershell
kubectl port-forward -n online-boutique service/frontend 8088:80
```

Open:

```text
http://127.0.0.1:8088
```

Verified on 2026-06-04:

- `curl -I http://127.0.0.1:8088` returned `HTTP/1.1 200 OK`.
- `curl -L http://127.0.0.1:8088` returned the Online Boutique homepage HTML.

## Restart After Reboot

After restarting Windows, Docker Desktop should be running first. Then run:

```powershell
.\FinalProject\scripts\resume-online-boutique.ps1
```

This starts Minikube if needed, removes old terminal Pods left by the previous
Minikube session, restarts the Online Boutique deployments, waits for the
frontend endpoint, and opens local access at:

```text
http://127.0.0.1:8088
```

`kubectl port-forward` is a foreground command. Keep that terminal open while using the web frontend.

Useful options:

```powershell
# Use a different local port if 8088 is occupied.
.\FinalProject\scripts\resume-online-boutique.ps1 -LocalPort 8089

# Validate cluster recovery without starting foreground port forwarding.
.\FinalProject\scripts\resume-online-boutique.ps1 -NoPortForward

# Skip deployment restart when the cluster is already known to be healthy.
.\FinalProject\scripts\resume-online-boutique.ps1 -SkipRolloutRestart
```

If Minikube is already running and the Pods are already healthy, the lightweight
frontend-only command is:

```powershell
.\FinalProject\scripts\port-forward-frontend.ps1
```

## Manual Recovery Commands

If the scripts are not used, run the following commands from
`D:\Study\SoftwareTesting` after Docker Desktop is running:

```powershell
minikube start
kubectl get namespace online-boutique
kubectl delete pod -n online-boutique --field-selector=status.phase=Failed --ignore-not-found
kubectl delete pod -n online-boutique --field-selector=status.phase=Succeeded --ignore-not-found
kubectl get deployment -n online-boutique -o name | ForEach-Object { kubectl rollout restart $_ -n online-boutique }
kubectl wait --for=condition=available deployment --all -n online-boutique --timeout=300s
kubectl get pods -n online-boutique -o wide
kubectl get endpointslices -n online-boutique -l kubernetes.io/service-name=frontend -o wide
kubectl port-forward -n online-boutique service/frontend 8088:80
```

If `kubectl get namespace online-boutique` reports that the namespace does not
exist, deploy the system again:

```powershell
.\FinalProject\scripts\deploy-online-boutique.ps1
```

## Current Notes

- Docker was already running.
- Minikube existed but was stopped; it was started before deployment.
- The old `sock-shop` namespace was deleted after deployment to free resources.
- Existing `monitoring` and `chaos-testing` namespaces were kept because they are useful for later Prometheus/Grafana monitoring and ChaosMesh fault injection.
- Direct access through `http://192.168.49.2:32493` was unreliable from Windows, so `kubectl port-forward` is the recommended local access method.
