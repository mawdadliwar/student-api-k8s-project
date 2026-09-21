# Task 7: Monitoring & Observability — Capacity Analysis

Student Management API platform — Kind Kubernetes cluster (single node:
`student-platform-control-plane`), namespace `student-platform-tf`.

---

## 1. Host & Cluster Capacity

| Resource | Total | Notes |
|---|---|---|
| Host RAM | 5.7 GiB | Native Ubuntu dual-boot laptop (AMD Ryzen 5 3500U, 8 cores) |
| Host Swap | 4.0 GiB | Has been used under memory pressure during this project |
| Host disk (root partition) | 39 GB | Historically tight on free space |
| Kubernetes nodes | 1 (control-plane only) | Originally a 3-node cluster (control-plane + 2 workers); both worker containers were removed entirely due to severe host memory pressure — a deliberate decision to continue with a single-node cluster rather than recreate the 3-node setup |

This is a **development/training environment**, not a production-sized
cluster. All capacity figures below should be read in that context — the
numbers demonstrate correct instrumentation and reasonable headroom for this
scale, not production capacity planning.

---

## 2. Observed Resource Usage (via `kubectl top` / Prometheus)

### Node-level

```
kubectl top nodes
NAME                              CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
student-platform-control-plane    199m         2%       958Mi           16%
```

At the single node's baseline load (running the full stack: kube-system
components, student-api, Prometheus, Grafana, Loki, Promtail), CPU usage is
very low (2%) and memory usage is moderate (16%, ~958 MiB of the node's
allocatable memory). There is substantial headroom at the node level under
normal conditions.

**However**, the host has previously hit genuine memory pressure at the OS
level (not just node-allocatable level) — one incident during this project
recorded only **179 MiB free of 5.7 GiB**, with active swap usage, which
correlated with a container being killed (`SandboxChanged` event, exit code
255). This means **host-level memory pressure is a more binding constraint
than Kubernetes-reported node capacity** on this particular machine — a
distinction worth calling out explicitly, since `kubectl top nodes` alone
would not have caught it.

### Application (student-api)

| Metric | Requests | Limits | Observed |
|---|---|---|---|
| CPU | 100m | 300m | Low, well under limit during normal use |
| Memory | 128Mi | 256Mi | ~54 MB per process (`process_resident_memory_bytes`), well under both request and limit |
| Replicas | 2 | — | Both consistently scheduled onto the same node (only option, since there's one node now) |

The application has significant headroom under both its own limits and the
node's capacity at current (light, manual-testing-level) traffic.

### Monitoring Stack Components

| Component | CPU request/limit | Memory request/limit | Storage |
|---|---|---|---|
| Prometheus | (see `k8s/monitoring/prometheus.yaml`) | — | — |
| Grafana | (default) | — | — |
| Loki | 50m / 200m | 128Mi / 256Mi | 1Gi PVC (filesystem storage, single-binary mode) |
| Promtail | 50m / 150m | 64Mi / 128Mi | — (reads host `/var/log/pods` and `/var/lib/docker/containers`, no own storage) |

The monitoring stack itself was deliberately sized lightly (single-binary
Loki instead of the distributed/microservices mode, conservative resource
requests/limits on both Loki and Promtail) specifically because of the host's
known memory constraints — this was a design decision, not an oversight.

---

## 3. Storage Capacity

| Volume | Size | Used for | Growth pattern |
|---|---|---|---|
| `student-api` PVC | 100Mi | SQLite database file | Grows slowly with student records; currently trivial (single test record set) |
| `loki-pvc` | 1Gi | Log chunks + index (TSDB, filesystem object store) | Grows continuously with log volume from all pods; retention set to **168h (7 days)** in `loki-config.yaml`'s `limits_config.retention_period` |

**Loki retention risk:** at 1Gi total capacity with all cluster pods' logs
being shipped (16+ discovered targets, including all `kube-system`
components, not just the application), a 7-day retention window may fill the
PVC before the retention period naturally rolls old data off, especially if
any component starts log-spamming (e.g., during a crash loop, as happened
multiple times in this project). This should be monitored — see
Section 4.

**SQLite on a shared PVC:** already documented in earlier Task 4/5 findings —
this gives persistence but **not** real write concurrency or high
availability. Not re-litigated here, but relevant to any future capacity
discussion about scaling `student-api` replicas.

---

## 4. Headroom & Scaling Considerations

1. **CPU headroom is ample** at current usage (2% node-wide) — the
   application and monitoring stack could scale several times over on the CPU
   dimension alone before hitting the single node's CPU capacity.

2. **Memory headroom is real but thinner than it looks** — the 16%
   node-level figure understates host-level risk. The host has already hit
   near-zero free RAM once during this project (during monitoring stack
   buildout, before Prometheus/Grafana/Loki were even fully running).
   **Recommendation:** avoid running more than one "new component bring-up"
   at a time on this host, and keep an eye on `free -h` (not just
   `kubectl top`) during any new deployment.

3. **Loki's 1Gi PVC is the single most likely capacity constraint to bite
   first**, given it accumulates logs from the entire cluster continuously.
   **Recommendation:** add a Prometheus alert on Loki's own disk usage (not
   currently one of the 5 alert rules — a gap worth closing, similar to the
   missing CPU-based alert noted in `Task7_Incident_Scenarios.md`), or
   periodically check `kubectl exec -n student-platform-tf deploy/loki -- df -h /loki`.

4. **Single-node cluster is a hard capacity ceiling**, not just a current
   constraint — with the 2 worker nodes removed, there is no horizontal
   scaling headroom for the *cluster* itself (only for individual pod
   replicas on the one remaining node). Any true scale-testing would require
   either more host RAM or an external/cloud cluster.

5. **student-api replica count (currently 2)** could be increased for
   redundancy testing without immediate resource concern (CPU/memory
   headroom exists), but would not improve real write throughput given the
   SQLite-on-shared-PVC limitation — any capacity planning for write-heavy
   load would need a database migration (e.g., to PostgreSQL), not just more
   replicas.

---

## 5. Summary

At current (development/testing-level) load, the platform has comfortable CPU
headroom and adequate — but not generous — memory headroom, constrained more
by host-level RAM than by Kubernetes-reported node capacity. The most
concrete near-term capacity risk is Loki's 1Gi log storage volume, which has
no dedicated alert yet. The most fundamental long-term constraint is the
single-node cluster itself, a deliberate trade-off accepted earlier in the
project due to host memory pressure.

*Prepared as part of Task 7 (Monitoring, Observability & Logging) deliverables.*
