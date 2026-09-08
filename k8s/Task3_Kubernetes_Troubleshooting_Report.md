# Task 3 — Kubernetes Troubleshooting Report

**Status:** Complete — 3 of 3 required incidents documented
**Project:** Student Management API — Local Kubernetes Infrastructure & Cluster Preparation
**Date:** September 8, 2026

Each incident below follows the required methodology:
`Problem → Symptoms → Investigation → Commands/Evidence → Root Cause → Resolution → Validation → Lessons Learned`

---

## Incident 1 — Pod Failure (Missing ConfigMap Reference)

### Problem
An intentionally broken `Deployment` (`broken-app`) was created in the `student-platform` namespace. Its container was configured to load environment variables from a ConfigMap (`app-config-missing`) that does not exist in the cluster.

### Symptoms
```bash
kubectl get pods -n student-platform -l app=broken-app -w
```
```
NAME                         READY   STATUS                       RESTARTS   AGE
broken-app-5dfcdf874-6h7fw   0/1     ContainerCreating            0          0s
broken-app-5dfcdf874-6h7fw   0/1     CreateContainerConfigError   0          1s
```
The Pod was scheduled but never became `Ready`, stuck in `CreateContainerConfigError`.

### Investigation
Followed the recommended order: `get` (confirmed abnormal status) → `describe` (to inspect Events) — `logs` was correctly ruled out first, since the container had never actually started (no process was ever running to produce log output; `CreateContainerConfigError` occurs before container start).

### Commands / Evidence
```bash
kubectl describe pod -n student-platform -l app=broken-app
```
Key evidence from the `Events` section:
```
Normal   Scheduled  ...  default-scheduler  Successfully assigned student-platform/broken-app-... to student-platform-worker2
Normal   Pulled     ...  kubelet            Container image "nginx:1.27-alpine" already present on machine
Warning  Failed     ...  kubelet            spec.containers{broken-app}: Error: configmap "app-config-missing" not found
```
Also visible in the container's `State`:
```
State:          Waiting
  Reason:       CreateContainerConfigError
Environment Variables from:
  app-config-missing  ConfigMap  Optional: false
```

### Root Cause
The Pod spec referenced a ConfigMap (`app-config-missing`) via `envFrom.configMapRef` that did not exist in the `student-platform` namespace. Scheduling and image pull both succeeded — the failure occurred specifically at the container-configuration step, before the container process could be created.

### Resolution
Created the missing ConfigMap:
```bash
kubectl create configmap app-config-missing --from-literal=APP_ENV=training -n student-platform
```
No changes to the Deployment itself were needed — Kubernetes automatically retried container creation once the referenced ConfigMap became available.

### Validation
```bash
kubectl get pods -n student-platform -l app=broken-app -w
# broken-app-5dfcdf874-6h7fw   1/1     Running   0   5m11s
```
Final `describe` confirmed the sequence of Events: `Scheduled` → (repeated) `Failed` while the ConfigMap was missing → `Pulled` → `Created` once resolved.

### Lessons Learned
- `CreateContainerConfigError` specifically signals a **pre-start configuration problem** (missing ConfigMap/Secret reference), distinct from image-pull errors or crash-looping application code — the Events section names the exact missing object, avoiding guesswork.
- `kubectl logs` is the wrong first tool when a container has never started; `kubectl describe` (and its Events) is the correct entry point in that case — matches the `get` → `describe` → `logs` decision order emphasized in the task (section 18).
- Kubernetes retries failed container creation automatically once the missing dependency is resolved — no need to delete/recreate the Pod or Deployment, reinforcing the task's guidance not to delete-and-recreate before understanding root cause.

---

## Incident 2 — Image Problem (Invalid / Nonexistent Container Image)

### Problem
A `Deployment` (`bad-image-app`) was created in the `student-platform` namespace referencing a container image that does not exist in any registry: `this-image-definitely-does-not-exist:v99`.

### Symptoms
```bash
kubectl get pods -n student-platform -l app=bad-image-app -w
```
```
NAME                            READY   STATUS             RESTARTS   AGE
bad-image-app-xxxxxxxxxx-xxxxx  0/1     ContainerCreating  0          0s
bad-image-app-xxxxxxxxxx-xxxxx  0/1     ErrImagePull       0          2s
bad-image-app-xxxxxxxxxx-xxxxx  0/1     ImagePullBackOff   0          17s
```
The Pod cycled between `ErrImagePull` and `ImagePullBackOff` and never reached `Running`.

### Investigation
Followed `get` → `describe` (Events). `logs` was not applicable — no container process was ever created, since the failure occurred entirely at the image-pull stage, before the container could start.

### Commands / Evidence
```bash
kubectl describe pod -n student-platform -l app=bad-image-app
```
Key evidence from the `Events` section:
```
Normal   Scheduled  ...  default-scheduler  Successfully assigned student-platform/bad-image-app-... to student-platform-worker
Normal   Pulling    ...  kubelet            Pulling image "this-image-definitely-does-not-exist:v99"
Warning  Failed     ...  kubelet            Failed to pull image "this-image-definitely-does-not-exist:v99":
                                             failed to resolve reference "docker.io/library/this-image-definitely-does-not-exist:v99":
                                             pull access denied, repository does not exist or may require authorization
Warning  Failed     ...  kubelet            Error: ErrImagePull
Normal   BackOff    ...  kubelet            Back-off pulling image "this-image-definitely-does-not-exist:v99"
Warning  Failed     ...  kubelet            Error: ImagePullBackOff
```

### Root Cause
The image name/tag referenced in the Deployment spec (`this-image-definitely-does-not-exist:v99`) does not exist in Docker Hub (`docker.io/library/...`) — neither the repository nor the tag are valid. The kubelet could not resolve or pull the image, so the container was never created.

### Resolution
Corrected the image reference directly on the live Deployment:
```bash
kubectl set image deployment/bad-image-app bad-image-app=nginx:1.27-alpine -n student-platform
```

### Validation
```bash
kubectl get pods -n student-platform -l app=bad-image-app -w
# bad-image-app-5bf55778b-twhqx   1/1     Running   0   7s
```
The Pod reached `1/1 Running` immediately once a valid, resolvable image was supplied.

### Lessons Learned
- `ErrImagePull` → `ImagePullBackOff` is **not a single, final error** — it's an exponential backoff retry cycle (the kubelet deliberately waits longer between each retry: e.g. 10s, 20s, 40s...) so it doesn't hammer the registry with continuous failed requests. `ImagePullBackOff` means "waiting before the next retry," not "permanently failed."
- This is a distinct failure class from Incident 1: Incident 1 failed at the **container-configuration** step (`CreateContainerConfigError`, after a successful image pull); Incident 2 failed earlier, at the **image-pull** step itself, before configuration or container creation were ever attempted.
- `kubectl set image` is a fast, useful tool for live corrections during troubleshooting, but it edits the **live cluster state only** — it does not update the underlying YAML manifest. Any manifest backing this Deployment must be updated separately to keep declarative source-of-truth in sync with the cluster (otherwise a future `kubectl apply -f` would silently revert the fix).

---

## Incident 3 — Service Problem (Selector / Label Mismatch)

### Problem
A `Service` (`broken-svc`) was created in the `student-platform` namespace with a `selector` (`app: bad-image-app-WRONG-LABEL`) that did not match the actual label on any existing Pod.

### Symptoms
The Service itself was created successfully and was assigned a stable ClusterIP, showing no obvious error at the Service level:
```bash
kubectl get svc broken-svc -n student-platform
```
```
NAME         TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
broken-svc   ClusterIP   10.96.27.219   <none>        80/TCP    8s
```
However, the Service had no backing Pods:
```bash
kubectl get endpoints broken-svc -n student-platform
```
```
NAME         ENDPOINTS   AGE
broken-svc   <none>      9s
```

### Investigation
`get svc` (confirmed the Service exists and has a ClusterIP — nothing looked wrong at this level) → `get endpoints` (revealed the real problem: no Endpoints were populated) → `get pods --show-labels` (compared actual Pod labels against the Service's selector) → `describe svc` (confirmed the exact selector configured on the Service).

### Commands / Evidence
```bash
kubectl get pods -n student-platform --show-labels
```
```
NAME                            READY   STATUS    LABELS
bad-image-app-5bf55778b-twhqx   1/1     Running   app=bad-image-app,pod-template-hash=5bf55778b
```
```bash
kubectl describe svc broken-svc -n student-platform
```
```
Selector:     app=bad-image-app-WRONG-LABEL
Endpoints:    (empty)
```
The Service selector (`app=bad-image-app-WRONG-LABEL`) did not match the Pod's actual label (`app=bad-image-app`).

### Root Cause
The `selector` field in the Service manifest did not match the `labels` on any existing Pod. A Service with a non-matching selector is created successfully by the API (it's valid, well-formed configuration) and receives a ClusterIP, but Kubernetes' Endpoints/EndpointSlice controller has no Pods to attach — the Service is effectively a dead end with nothing behind it.

### Resolution
Corrected the selector to match the real Pod label:
```bash
kubectl patch svc broken-svc -n student-platform -p '{"spec":{"selector":{"app":"bad-image-app"}}}'
```

### Validation
```bash
kubectl get endpoints broken-svc -n student-platform
# broken-svc   10.244.1.4:80   80s
```
Endpoints populated correctly with the Pod's IP. Confirmed end-to-end with an actual connection test:
```bash
kubectl port-forward -n student-platform svc/broken-svc 8081:80
curl -v http://localhost:8081
```
```
< HTTP/1.1 200 OK
< Server: nginx/1.27.5
...
Welcome to nginx!
```

### Lessons Learned
- A Service with no matching Pods does **not** surface as an error at the Service level — `kubectl get svc` shows it as perfectly healthy (valid ClusterIP, no warnings). The only way to detect this class of problem is to check `kubectl get endpoints` (or the newer `EndpointSlice` object) specifically — the Service object alone is not sufficient evidence of a working Service.
- This incident is a fundamentally different failure category from Incidents 1 and 2: those were Pod/container-level problems (a missing ConfigMap, an invalid image); this one was a **relationship problem between two separate resources** (Service selector vs. Pod labels) where each resource was individually valid on its own.
- Diagnosing selector mismatches requires explicitly comparing the Service's `Selector:` field (from `describe svc`) against the Pod's actual `LABELS` (from `get pods --show-labels`) side by side — the difference can be a single extra word or typo and is easy to miss without a direct, literal comparison of the two strings.

---

## Summary Across All Incidents

| # | Category | Root Cause | Detection Signal | Fix |
|---|---|---|---|---|
| 1 | Pod / container config | Missing ConfigMap referenced by `envFrom` | `CreateContainerConfigError` + Events naming the missing object | Create the missing ConfigMap |
| 2 | Image pull | Nonexistent image name/tag | `ErrImagePull` → `ImagePullBackOff` cycle in Events | Correct the image reference |
| 3 | Service / networking | Service selector didn't match Pod labels | Empty `Endpoints` despite a healthy-looking Service | Patch the selector to match Pod labels |

**Overall lesson:** each incident required a different tool/signal to diagnose (Events for 1 and 2, `get endpoints` for 3), reinforcing that `kubectl get` → `describe` → `logs` → `get endpoints` together — not any single command — form the real troubleshooting toolkit, and that the correct starting point depends on which layer (container config, image pull, or service networking) is actually failing.

---

## Status — Remaining Work (Task 3 overall, outside this report)

- Scheduling investigation write-up (separate documentation, data already collected from scaling test)
- Kubernetes architecture explanation (control plane/worker components)
- Architecture diagram (`Task3_Kubernetes_Architecture`)
- Known limitations and recommendations (final section of Operations Report)
