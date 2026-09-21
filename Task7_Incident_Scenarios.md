# Task 7: Monitoring & Observability — Incident Scenarios

This document records five incident scenarios encountered and resolved while building
out the monitoring, alerting, and logging stack (Prometheus, Grafana, Loki/Promtail)
for the Student API platform on Kubernetes (kind cluster, namespace
`student-platform-tf`).

Each scenario follows the same structure: **Detection → Diagnosis → Root Cause →
Resolution → Prevention / Lessons Learned**.

Two of the five required categories — **Application Down** and **Frequent Pod
Restarts** — are documented below using *real* incidents that occurred organically
during this project, with actual command output and log evidence. The remaining
three categories — **High Error Rate**, **High Memory Usage**, and **High CPU
Usage** — did not occur naturally (the application ran cleanly throughout: 0% error
rate, ~54 MB memory, ~2% CPU on the node), so they are documented as **synthetic
test scenarios**, run deliberately to validate that the corresponding alert rules
and dashboard panels actually fire and recover correctly. This is noted explicitly
in each section rather than presented as an organic failure.

---

## Scenario 1: Application Down — Cluster-Wide Networking Outage (Clock Skew)

**Category:** Application Down
**Severity:** Critical
**Type:** Real incident (recurred 3 times during this project)

### Detection
While configuring the Grafana → Prometheus datasource, adding the datasource failed
with a DNS resolution error:

```
dial tcp: lookup prometheus: i/o timeout
```

A `wget` from inside the Grafana pod to `http://prometheus:9090` also failed with
`bad address`. This pattern recurred twice more later in the project — once
affecting `metrics-server` and `local-path-provisioner` (both crash-looping), and
once affecting Promtail's ability to push logs to Loki (`context deadline
exceeded`).

### Diagnosis
1. `kubectl get pods -n kube-system -l k8s-app=kube-dns` showed both CoreDNS pods
   as `Running` but **not Ready** (`0/1`), with `RESTARTS` incrementing and `AGE`
   showing `<invalid> ago`.
2. CoreDNS logs showed repeated `Unauthorized` errors when trying to `list`
   `Namespace`/`Service`/`EndpointSlice`.
3. `kube-proxy` logs showed the identical `Unauthorized` pattern watching
   `Service`/`Node`/`EndpointSlice`/`ServiceCIDR`.
4. `kubectl get clusterrole system:coredns -o yaml` and
   `kubectl get clusterrolebinding system:coredns -o yaml` confirmed RBAC was
   correctly configured — ruling out a permissions bug.
5. `kube-apiserver` logs revealed the actual cause:

```
"Unable to authenticate the request" err="[invalid bearer token, service account token is not valid yet]"
```

### Root Cause
A clock-skew event (most likely caused by the laptop entering suspend/resume,
since this is a native dual-boot Ubuntu install, not a VM) caused the API server
to briefly reject service account tokens as "not valid yet." Although the host
clock self-corrected (confirmed identical via `date` vs.
`docker exec student-platform-control-plane date` — containers share the host
kernel clock), CoreDNS, kube-proxy, and other system pods remained stuck holding
stale/rejected tokens issued during the skew window. Because CoreDNS and
kube-proxy could not authenticate to the API server, cluster DNS resolution and
Service-to-Pod routing (iptables/NAT rules) both broke — which meant any
in-cluster service name (`prometheus`, `loki`, `student-api-svc`, etc.) became
unreachable, i.e., effectively "down" from every other pod's perspective even
though the underlying pods were still running.

### Resolution
Force the affected pods to re-authenticate with fresh tokens:

```bash
kubectl delete pods -n kube-system -l k8s-app=kube-dns
kubectl delete pod -n kube-system -l k8s-app=kube-proxy
```

Confirmed recovery each time via:

```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns   # 1/1 Running, 0 restarts
kubectl exec -it -n student-platform-tf deploy/grafana -- wget -qO- http://prometheus:9090/-/healthy
# → "Prometheus Server is Healthy"
```

The same fix pattern was reused for `metrics-server`
(`kubectl rollout restart deployment metrics-server -n kube-system`) and
`local-path-provisioner`
(`kubectl rollout restart deployment local-path-provisioner -n local-path-storage`)
when they showed the identical symptom.

### Prevention / Lessons Learned
- This issue **recurred at least 3 times** across the project, always with the
  same signature: `AGE` showing `<invalid> ago`, restart count incrementing, and
  either `dial tcp 10.96.0.1:443: i/o timeout` or
  `invalid bearer token, service account token is not valid yet` in logs.
- Documented as a **standing known issue** in the Runbook with the fix as the
  standard first response, rather than re-diagnosing from scratch each time.
- The `Application Down` alert rule (`up{job="student-api"} IS BELOW 1`, with
  no-data handling set to **Alerting**) is specifically designed to catch this
  class of failure — if a target disappears from Prometheus entirely (as would
  happen if DNS/networking broke), the alert fires on missing data rather than
  staying silently "Normal."
- A longer-term mitigation worth investigating: enabling NTP/`timedatectl` more
  aggressively on the host, or increasing the API server's token clock-skew
  tolerance, to reduce how often this triggers.

---

## Scenario 2: Frequent Pod Restarts — metrics-server Crash Loop

**Category:** Pod Restart
**Severity:** Medium
**Type:** Real incident

### Detection
Before starting Loki setup, a routine pre-check (`kubectl top nodes`) returned:

```
error: Metrics API not available
```

despite metrics-server having been previously installed and confirmed working.

### Diagnosis
```bash
kubectl get pods -n kube-system -l k8s-app=metrics-server
# NAME                               READY   STATUS   RESTARTS      AGE
# metrics-server-7c5fdf4664-vrj8t    0/1     Error    2 (10s ago)   7d4h
```

The pod was actively crash-looping (2 restarts in the last 10 seconds — an active
loop, not a stale historical count). Logs showed:

```
panic: unable to load configmap based request-header-client-ca-file:
  Get "https://10.96.0.1:443/api/v1/namespaces/kube-system/configmaps/extension-apiserver-authentication":
  dial tcp 10.96.0.1:443: i/o timeout
```

### Root Cause
Same underlying cause as Scenario 1 (stale service account token from a prior
clock-skew event) — metrics-server could not reach the Kubernetes API server to
load a required ConfigMap at startup, so it panicked and crashed immediately, and
kept doing so every restart because the token never refreshed on its own.

### Resolution
```bash
kubectl rollout restart deployment metrics-server -n kube-system
```

Confirmed fixed:

```bash
kubectl get pods -n kube-system -l k8s-app=metrics-server
# 1/1 Running, 0 restarts

kubectl top nodes
# student-platform-control-plane   199m   2%   958Mi   16%
```

### Prevention / Lessons Learned
- A `rollout restart` is a safe, low-risk first response to any pod stuck in
  `CrashLoopBackOff`/`Error` with the `dial tcp ... i/o timeout` signature —
  it forces a fresh service account token without needing to touch RBAC or
  configuration.
- The **Frequent Pod Restarts** alert rule (`resets(up{job="student-api"}[15m])
  IS ABOVE 0`) is scoped to the application itself; system-level crash loops
  like this one are instead caught by routine `kubectl get pods -n kube-system`
  health checks, which are now part of the standard pre-flight checklist before
  starting new monitoring work (documented in the Runbook).

---

## Scenario 3: High Error Rate (Synthetic Test)

**Category:** High Error Rate
**Severity:** N/A (test scenario)
**Type:** Synthetic — the application produced 0% real errors throughout the
project (the Error Rate panel legitimately showed "No data"), so this alert was
validated by deliberately generating 5xx responses rather than waiting for one to
occur naturally.

### Test Procedure
1. Generate a burst of requests against a non-existent or intentionally-broken
   endpoint to produce 5xx responses, e.g.:
   ```bash
   for i in $(seq 1 50); do
     curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/students/invalid-trigger
   done
   ```
   *(or, more realistically, temporarily scale the Deployment to 0 replicas for
   a few seconds while sending traffic through the Service, to produce real
   connection/5xx failures)*
2. Watch the **Error Rate** panel on the "Student API - Overview" Grafana
   dashboard and the **High Error Rate** alert rule's state.

### Expected Result
- The PromQL query
  `sum(rate(student_api_requests_total{http_status=~"5.."}[5m])) /
  sum(rate(student_api_requests_total[5m])) * 100`
  rises above the `5` threshold.
- The `High Error Rate` alert rule transitions from `Normal` → `Pending` →
  `Alerting` within the 1m evaluation interval + pending period.
- Once traffic returns to normal, the rate decays and the alert returns to
  `Normal`.

### Status
**Not yet executed** — recommended as a follow-up hands-on test to capture real
before/after screenshots of the panel and the alert state transition as evidence
for the final report.

---

## Scenario 4: High Memory Usage (Synthetic Test)

**Category:** High Memory Usage
**Severity:** N/A (test scenario)
**Type:** Synthetic — the application's real memory usage was measured at ~54 MB
throughout the project, well under the 200 MB alert threshold, so this was never
organically triggered.

### Test Procedure
Temporarily lower the alert threshold to a value below current usage to confirm
the rule fires correctly, then restore it, e.g.:
```
Threshold: IS ABOVE 40   (instead of 200)
```
Alternatively, generate real memory pressure by sending a sustained burst of
concurrent requests (e.g., 100+ concurrent POST /students) to temporarily raise
the Python process's working set.

### Expected Result
- `process_resident_memory_bytes{job="student-api"} / 1024 / 1024` exceeds the
  (temporarily lowered) threshold.
- The `High Pod Memory Usage` alert rule fires and clears once load subsides or
  the threshold is restored to 200.

### Status
**Not yet executed** — recommended as a follow-up hands-on test.

---

## Scenario 5: High CPU Usage (Synthetic Test)

**Category:** High CPU Usage
**Severity:** N/A (test scenario)
**Type:** Synthetic. **Note:** No CPU-based alert rule currently exists in the
5 alert rules built for this project (the 5 built were: High Error Rate, High
Latency, Application Down, High Pod Memory Usage, and Frequent Pod Restarts —
substituting "High Latency" for "High CPU" since no CPU metric was available
from the application's own `/metrics` endpoint, and no cluster-level CPU metric
source such as cAdvisor/kube-state-metrics is scraped by this Prometheus
instance).

### Recommended Follow-up
To properly cover this category, one of two paths is needed before this scenario
can be executed and documented with real evidence:
1. Add a CPU-based alert using `process_cpu_seconds_total{job="student-api"}`
   (already confirmed available — see the `__name__` label list gathered during
   Loki troubleshooting), via `rate(process_cpu_seconds_total{job="student-api"}[5m])`.
2. Then generate CPU load (e.g., a tight request loop or a CPU-bound endpoint)
   and confirm the new alert transitions to `Alerting`.

### Status
**Not yet executed** — a 6th alert rule (CPU-based) should be added as a
follow-up before this scenario can be completed with real evidence.

---

## Summary Table

| # | Scenario | Category | Type | Status |
|---|----------|----------|------|--------|
| 1 | Clock-skew cluster networking outage | Application Down | Real | ✅ Documented with full evidence |
| 2 | metrics-server crash loop | Pod Restart | Real | ✅ Documented with full evidence |
| 3 | Simulated 5xx burst | High Error Rate | Synthetic | ⏳ Test procedure defined, not yet run |
| 4 | Simulated memory pressure | High Memory Usage | Synthetic | ⏳ Test procedure defined, not yet run |
| 5 | Simulated CPU load | High CPU Usage | Synthetic | ⏳ Needs new alert rule first |

*Prepared as part of Task 7 (Monitoring, Observability & Logging) deliverables.*
