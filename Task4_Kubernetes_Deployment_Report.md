# Task 4: Kubernetes Deployment Report

## Architecture & Components
- **Cluster**: Kind Multi-Node Cluster (`student-platform`) with 1 Control-Plane and 2 Workers.
- **Storage**: PersistentVolume (PV) and PersistentVolumeClaim (PVC) hosting persistent SQLite database (`/app/data`).
- **Workload**: Deployment (`student-api`) running 2 Replicas with RollingUpdate strategy.
- **Networking**: ClusterIP Service (`student-api-svc`) exposed via NGINX Ingress Controller (`student-api-ingress`) mapping host `student-api.local`.

## Verification & Key Evidence
1. **PVC Data Persistence**: verified concurrent DB writes from multiple Pods pointing to single PVC.
2. **Ingress Routing**: Executed `curl -H "Host: student-api.local" http://localhost:8080/students` returning HTTP 200 with 41 persistent student records.
3. **Rolling Updates & Rollback**: Zero-downtime update from `v1.0` to `v1.1` verified via `kubectl rollout status`, followed by successful rollback from bad image tag.
