# Task 7: Monitoring & Observability Architecture Design

## 1. Executive Summary
This document establishes the architectural blueprint for the Student Management Platform's observability stack using Prometheus, Grafana, and Loki.

---

## 2. Telemetry Ingestion Architecture

### Data Source & Collector Mappings
* **Infrastructure & Nodes**: Metrics collected via `node-exporter` (CPU, Memory, Disk, Network).
* **Kubernetes Control Plane & Workloads**: Metrics gathered via `kube-state-metrics` and `cAdvisor` (Pod status, restarts, container limits).
* **Application Layer**: Exposed via native Flask Prometheus metrics at `/metrics` endpoint.
* **Logs Pipeline**: Container stdout/stderr collected via `Promtail` / `Grafana Alloy` and forwarded to Loki.

---

## 3. Four-Layer Monitoring Framework

| Layer | Metric Source | Primary Metrics Tracked | Storage Target |
| :--- | :--- | :--- | :--- |
| **Layer 1: Infrastructure** | Node Exporter | CPU utilization, Memory usage, Disk I/O | Prometheus TSDB |
| **Layer 2: Kubernetes** | cAdvisor / Kube-State | Pod counts, Container restarts, Deployment availability | Prometheus TSDB |
| **Layer 3: Application** | Flask `/metrics` | `student_api_requests_total`, `student_api_request_duration_seconds` | Prometheus TSDB |
| **Layer 4: Database** | Flask / App Hooks | Connection status, Query latencies, Disk PVC capacity | Prometheus TSDB |

---

## 4. Operational Visualization & Alerting
* **Dashboard Engine**: Grafana serving single-pane-of-glass views ("Student Management Platform Operations").
* **Log Aggregation Engine**: Loki storing structured/unstructured operational logs.
* **Alert Engine**: Prometheus Alertmanager evaluating rule thresholds (High Error Rate, Pod CrashLoop, CPU Spikes).
