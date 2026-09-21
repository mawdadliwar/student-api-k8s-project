# Task 7: Monitoring & Observability — Operations Runbook

Student Management API platform — Kind Kubernetes cluster, namespace
`student-platform-tf`.

This runbook covers day-to-day operation of the monitoring stack: how to access
each tool, standard health checks, alert response procedures, and known issues
with their fixes.

---

## 1. Stack Overview

| Component | Purpose | Namespace | Access |
|---|---|---|---|
| Prometheus | Metrics collection & storage | `student-platform-tf` | `kubectl port-forward svc/prometheus -n student-platform-tf 9090:9090` |
| Grafana | Dashboards & alerting UI | `student-platform-tf` | `kubectl port-forward svc/grafana -n student-platform-tf 3001:3000` (default creds `admin`/`admin`, change on first login) |
| Loki | Log storage & querying | `student-platform-tf` | Via Grafana Explore/datasource, or `kubectl port-forward svc/loki -n student-platform-tf 3100:3100` |
| Promtail | Log shipping agent (DaemonSet) | `student-platform-tf` | No direct access needed; debug via `kubectl logs` |
| student-api | The application itself | `student-platform-tf` | Service `student-api-svc`, NodePort 30032 (host access via port-forward — see Known Issue 1) |
| metrics-server | Node/pod resource metrics | `kube-system` | `kubectl top nodes` / `kubectl top pods` |

**Note on local port-forwards:** this environment repeatedly hit "address
already in use" from leftover `kubectl port-forward` processes from previous
sessions. If a forward fails with `bind: address already in use`, either use a
different local port (e.g. `3002` instead of `3001`) or find and kill the
stale process: `lsof -i :<port>` then `kill <PID>`.

---

## 2. Daily / Pre-Work Health Check

Run before starting any new monitoring work, to catch issues early rather than
mid-task:

```bash
# Overall pod health across all namespaces
kubectl get pods -A | grep -v Running

# Specifically check the components most prone to the recurring clock-skew issue
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl get pods -n kube-system -l k8s-app=kube-proxy
kubectl get pods -n kube-system -l k8s-app=metrics-server
kubectl get pods -n local-path-storage

# Confirm metrics-server is actually returning data (not just Running)
kubectl top nodes

# Confirm the monitoring stack itself is healthy
kubectl get pods -n student-platform-tf -l app=prometheus
kubectl get pods -n student-platform-tf -l app=grafana
kubectl get pods -n student-platform-tf -l app=loki
kubectl get pods -n student-platform-tf -l app=promtail
```

If any pod shows `RESTARTS ... (<invalid> ago)`, go straight to **Known Issue 1**
below before investigating further.

---

## 3. Alert Response Procedures

All 5 alert rules live in Grafana under **Alerting → Alert rules**, folder
`student-api-alerts`, evaluated every 1 minute.

### High Error Rate
- **Trigger:** >5% of requests returning 5xx over a 5-minute window.
- **First response:** Check recent deployments/rollouts
  (`kubectl rollout history deployment/student-api -n student-platform-tf`).
  Check application logs via Loki (query: `{app="student-api"} |= "error"`)
  or `kubectl logs`.
- **Escalation:** If tied to a recent code change, consider
  `kubectl rollout undo deployment/student-api -n student-platform-tf`.

### High Latency (p95)
- **Trigger:** p95 response time >1s over a 5-minute window.
- **First response:** Check `kubectl top pods -n student-platform-tf` for CPU
  saturation. Check database (SQLite/PVC) I/O — note SQLite is single-writer;
  concurrent write load can serialize and slow requests (see
  Task4/Task5 findings on PVC + SQLite limitations).
- **Escalation:** Consider scaling replicas, though note SQLite-on-shared-PVC
  does not give true write concurrency (documented limitation, not a monitoring
  fix).

### Application Down
- **Trigger:** `up{job="student-api"}` is below 1 (target missing counts as
  "Alerting", not "no data").
- **First response:** `kubectl get pods -n student-platform-tf -l app=student-api`.
  If pods are Running but the target is still missing from Prometheus, suspect
  the **clock-skew networking issue** — check Known Issue 1 immediately.
- **Escalation:** If pods are actually crashed, check
  `kubectl describe pod <name> -n student-platform-tf` for the reason and
  `kubectl logs <name> -n student-platform-tf --previous`.

### High Pod Memory Usage
- **Trigger:** `process_resident_memory_bytes` >200 MB.
- **First response:** Check for a memory leak pattern over time in the
  Grafana panel (steadily climbing vs. a one-off spike). Check recent request
  volume/patterns.
- **Escalation:** Restart the pod as an immediate mitigation
  (`kubectl delete pod <name> -n student-platform-tf`, the Deployment will
  recreate it) while investigating the root cause.

### Frequent Pod Restarts
- **Trigger:** `resets(up{job="student-api"}[15m])` above 0 (i.e., the target
  actually went down and came back within 15 minutes — not just alternating
  between replicas, which this query is specifically designed to avoid
  misreading as restarts).
- **First response:** `kubectl get pods -n student-platform-tf -l app=student-api`
  — check `RESTARTS` column and `kubectl describe pod` for the last
  termination reason (`OOMKilled`, `Error`, `Completed`, etc.).
- **Escalation:** Correlate with Loki logs around the restart timestamp to
  find the crash cause.

---

## 4. Known Issues

### Known Issue 1: Clock-Skew / Stale Service Account Token (Recurring)

**Symptom signature:**
- `kubectl get pods` shows `RESTARTS: N (<invalid> ago)` on system components
  (CoreDNS, kube-proxy, metrics-server, local-path-provisioner) or a pod stuck
  `CrashLoopBackOff`/not-Ready.
- Logs show `dial tcp 10.96.0.1:443: i/o timeout` or
  `invalid bearer token, service account token is not valid yet`.
- In-cluster service names (`prometheus`, `loki`, `grafana`, etc.) become
  unreachable from other pods even though the pods themselves are Running.

**Cause:** Host clock skew (most likely from laptop suspend/resume on this
native dual-boot install) causes the API server to briefly reject service
account tokens. Affected pods keep the stale/rejected token even after the
clock self-corrects.

**Standard fix (safe, low-risk, always try first):**
```bash
# For CoreDNS / kube-proxy specifically:
kubectl delete pods -n kube-system -l k8s-app=kube-dns
kubectl delete pod -n kube-system -l k8s-app=kube-proxy

# For any Deployment-managed component (metrics-server, local-path-provisioner, etc.):
kubectl rollout restart deployment <name> -n <namespace>
```
Wait ~20-30 seconds, then re-run the health check in Section 2 to confirm
recovery (`1/1 Running`, `0 restarts`, target `up` in Prometheus).

**This has recurred 3+ times in this project** — treat it as expected
background maintenance on this particular host setup, not a one-off anomaly.

### Known Issue 2: NodePort Services Not Reachable from Host

**Symptom:** `curl localhost:<nodeport>` or browser access to a NodePort
Service times out, even though the Service and pods are healthy.

**Cause:** This kind cluster's config has no `extraPortMappings`, which kind
requires to forward NodePort traffic to the host.

**Standard fix:** Use `kubectl port-forward` instead of relying on the
NodePort directly:
```bash
kubectl port-forward svc/<service-name> -n student-platform-tf <local-port>:<service-port>
```

**Permanent fix (not yet done):** Would require recreating the kind cluster
with `extraPortMappings` configured — deferred to avoid disrupting existing
PVC/data.

### Known Issue 3: Stale Local `kubectl port-forward` Processes

**Symptom:** New `port-forward` command fails with
`bind: address already in use`.

**Cause:** A previous `port-forward` from an earlier session/terminal is still
running in the background.

**Standard fix:** Use a different local port, or find and kill the process:
```bash
lsof -i :<port>
kill <PID>
```

---

## 5. Escalation / When to Stop and Reassess

- If the clock-skew issue (Known Issue 1) starts recurring within minutes of
  being fixed rather than days, treat it as a signal the host clock/NTP setup
  needs a permanent fix (`timedatectl set-ntp true`, verify with
  `timedatectl status`) rather than continuing to patch symptoms.
- If a real production-style incident occurs (data loss, PVC corruption,
  persistent app crash unrelated to known issues above), stop and do a full
  root-cause investigation rather than applying the standard fixes above —
  they are scoped specifically to the known issues documented here.

*Prepared as part of Task 7 (Monitoring, Observability & Logging) deliverables.*
