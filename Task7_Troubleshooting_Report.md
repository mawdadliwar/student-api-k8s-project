# Task 7: Monitoring & Observability — Troubleshooting Report

Student Management API platform — Kind Kubernetes cluster, namespace
`student-platform-tf`. This report consolidates every real incident encountered
while building the Prometheus/Grafana/Loki monitoring stack, in chronological
order, each with Detection, Root Cause, Resolution, and Prevention.

---

## Incident 1: NodePort Services Unreachable (No Host Port Binding)

**Detection:** `student-api-svc` (NodePort 30032) and `prometheus` (NodePort
30090) were both unreachable from the host browser/curl, despite the underlying
pods running fine.

**Root Cause:** The single-node kind cluster's config lacks `extraPortMappings`,
which kind requires to actually forward a host port into the container for
NodePort services. Without it, a NodePort Service only works from *inside* the
cluster network, not from the host.

**Resolution:** Used `kubectl port-forward` for both services as a workaround
instead of recreating the cluster:
```bash
kubectl port-forward svc/student-api-svc -n student-platform-tf 8080:80
kubectl port-forward svc/prometheus -n student-platform-tf 9090:9090
```

**Prevention:** Documented as a standing limitation of this cluster's config.
Any new service needing host access should default to `port-forward` rather
than assuming NodePort will "just work" from the browser. A future fix would be
recreating the kind cluster with `extraPortMappings` in its config — not done
here to avoid disrupting existing persistent data.

---

## Incident 2: Prometheus Scrape Target Misconfigured (Twice)

**Detection:** Prometheus target health showed the `student-api` target as
`down` / scrape errors.

**Root Cause (attempt 1):** The `prometheus-config` ConfigMap pointed at
`student-api:5001` — wrong Service name (the actual Service is
`student-api-svc`, not `student-api`).

**Root Cause (attempt 2, after fixing #1):** Still failing — the target was
`student-api-svc:5001`, using the container port (5001) instead of the
**Service** port (80). Kubernetes Services proxy Service-port → container-port
internally; other pods must talk to the Service port.

**Resolution:** Corrected the scrape target to `student-api-svc:80` and applied:
```bash
kubectl apply -f prometheus-configmap.yaml
kubectl rollout restart deployment/prometheus -n student-platform-tf
```
Confirmed target health became `up` with no scrape errors.

**Prevention:** When wiring up any new scrape target, always double-check
Service name *and* Service port (not container port) — a two-step verification
now part of the standard monitoring checklist.

---

## Incident 3: metrics-server — TLS Certificate Validation Failure

**Detection:** `kubectl top nodes` / `kubectl top pods` failed with an x509
certificate error.

**Root Cause:** `x509: cannot validate certificate` — the kubelet's serving
certificate on this kind cluster has no IP SANs, a common kind-specific issue,
so metrics-server's default TLS verification of kubelets fails.

**Resolution:**
```bash
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```
Confirmed working: `kubectl top nodes` / `kubectl top pods` return real data.

**Prevention:** `--kubelet-insecure-tls` is an accepted trade-off for local
kind clusters (not recommended for production, where kubelet certs should have
proper SANs). Documented as a kind-specific quirk, not a general fix.

---

## Incident 4 (Recurring): Cluster Networking Outage from Stale Service Account Tokens (Clock Skew)

This is the most significant and highest-impact incident of the project —
**it recurred at least 3 separate times**, breaking different components each
time. Full write-up with logs and evidence is in `Task7_Incident_Scenarios.md`
(Scenario 1: Application Down). Summarized here for completeness:

**Signature (always the same):**
- Affected pod(s) show `Running` but not `Ready`, or crash-looping.
- `AGE` in `kubectl get pods` shows `RESTARTS ... (<invalid> ago)`.
- Logs show either `dial tcp 10.96.0.1:443: i/o timeout` or
  `invalid bearer token, service account token is not valid yet`.

**Occurrences:**
1. CoreDNS + kube-proxy → broke DNS resolution and Service routing cluster-wide
   (discovered while connecting the Grafana → Prometheus datasource).
2. `local-path-provisioner` → stuck the `loki-pvc` PersistentVolumeClaim in
   `Pending` (couldn't provision storage). `metrics-server` → crash-looping
   again (see Incident 3's fix reused).
3. CoreDNS + kube-proxy again → broke Promtail's ability to push logs to Loki
   (`context deadline exceeded`).

**Root Cause:** A clock-skew event (likely triggered by laptop suspend/resume,
since this is a native Ubuntu dual-boot install) causes the API server to
briefly reject service account tokens as "not valid yet." Affected pods get
stuck holding stale tokens even after the clock self-corrects, because nothing
forces them to re-authenticate on their own.

**Resolution (same every time):** Force the stuck component to re-authenticate
by deleting/restarting its pod(s):
```bash
kubectl delete pods -n kube-system -l k8s-app=kube-dns
kubectl delete pod -n kube-system -l k8s-app=kube-proxy
# or, for a Deployment-managed component:
kubectl rollout restart deployment <name> -n <namespace>
```

**Prevention:** Documented as a **standing known issue** with a fast, standard
first response (see the Runbook's "Known Issues" section) — recognizing the
`<invalid> ago` + timeout/bearer-token signature now takes seconds instead of
requiring a full re-diagnosis each time.

---

## Incident 5: Promtail Configuration Bug Chain

**Detection:** After deploying Promtail (log shipping agent), Loki showed no
ingested log labels at all.

**Root Cause / Resolution — five distinct bugs found in sequence:**

1. **Duplicate YAML key** — `pipeline_stages` was defined twice in the scrape
   config, causing `CrashLoopBackOff` on startup.
   → Fixed by removing the duplicate.

2. **No writable volume for the positions file** — `positions.filename:
   /run/promtail/positions.yaml` had no volume mounted at `/run/promtail`,
   causing repeated `error writing positions file`.
   → Fixed by adding an `emptyDir` volume mounted at `/run/promtail`.

3. **Zero targets discovered (0/0)** — Promtail's Kubernetes service discovery
   auto-filters by node using the `$HOSTNAME` environment variable to match
   `spec.nodeName`, but inside any container `$HOSTNAME` defaults to the **pod
   name** (e.g. `promtail-jflj9`), not the real node name.
   → Fixed via the Downward API:
   ```yaml
   env:
     - name: HOSTNAME
       valueFrom:
         fieldRef:
           fieldPath: spec.nodeName
   ```

4. **Targets discovered but all Ready=FALSE, empty Path** — the multi-label
   `__path__` relabel_config used the default regex `(.*)`, which only
   captures *one* group even when matching multiple source labels joined by a
   separator — so `$1`/`$2`/`$3`/`$4` in the replacement were mostly empty.
   → Fixed with an explicit 4-group regex: `(.*)/(.*)/(.*)/(.*) `.

5. **Path still missing the first two segments even with the right regex** —
   Go's templating parses `$1_` as a reference to a variable literally named
   `"1_"` (which doesn't exist), not as `$1` followed by a literal underscore.
   → Fixed using the braced form: `${1}_${2}_${3}/${4}` in the replacement.

**Final confirmation:**
```bash
kubectl exec -it -n student-platform-tf deploy/loki -- wget -qO- 'http://localhost:3100/loki/api/v1/labels'
# {"status":"success","data":["app","container","filename","namespace","node_name","pod","stream"]}
```

**Prevention:** This chain illustrates the value of *verifying at each layer*
(discovery → target readiness → actual data arriving at Loki) rather than
assuming a single fix resolved the whole pipeline. Documented as a reference
for anyone debugging a similar Promtail multi-label relabeling setup.

---

## Cross-Cutting Lessons Learned

1. **Always verify Service name *and* Service port**, not container port, when
   wiring components together (Incident 2).
2. **`AGE ... <invalid> ago` + timeout/bearer-token errors** is a recognizable
   signature for the clock-skew issue — check for it first before deep-diving
   into RBAC or networking (Incident 4).
3. **A `rollout restart` / pod delete is often the correct, low-risk first
   response** to components stuck on stale auth state — it doesn't fix the
   root clock-skew cause, but it's a safe, fast mitigation.
4. **Multi-stage relabeling configs (Promtail) need layer-by-layer
   verification** — a pipeline can look "deployed successfully" while still
   being functionally broken at any of several stages (Incident 5).
5. **RBAC being correctly configured doesn't rule out authentication
   failures** — `Unauthorized` in logs can stem from an invalid/stale token
   just as easily as from a missing permission; both were checked explicitly
   before concluding root cause (Incident 4).

*Prepared as part of Task 7 (Monitoring, Observability & Logging) deliverables.*
