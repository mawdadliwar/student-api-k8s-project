# Task 5: Incident Reports & Root Cause Analyses (RCA)

## Incident: INC-001
- **Summary**: Student API reported as unresponsive from host environment.
- **Severity**: High (External Ingress traffic blocked).
- **Impact**: Clients attempting access on `localhost:8080` received TCP connection errors (`curl: 7`).
- **Symptoms**: `curl: (7) Failed to connect to localhost port 8080`.
- **Investigation**:
  1. Inspected Ingress Controller services: Controller listening on NodePorts `30447/TCP` (HTTP standard `80`)[cite: 3].
  2. Verified Ingress & Service endpoints: `student-api-svc` mapping port `80` to container port `5001`[cite: 3].
  3. Attempted `port-forward` on `5001` which failed because the Service target port abstraction exposed port `80`[cite: 3].
- **Root Cause**: Client requests were targeted at port `8080` instead of port `80` mapped by the NGINX Ingress controller, or lacking active port-forwarding to port `80`[cite: 3].
- **Resolution**: Routed traffic directly to `http://localhost/health` with Host header or mapped service port `80` to local `8080`[cite: 3].
- **Validation**: Successful `200 OK` HTTP responses from `/health` endpoint[cite: 3].
- **Lessons Learned**: Align environment port mappings across development documentation and Ingress rules[cite: 3].
- **Preventive Action**: Standardize port mappings in operations runbook and automated health-check scripts[cite: 3].

---

## Incident: INC-002 (CrashLoopBackOff)
- **Summary**: Newly generated Pods entered a continuous restart loop (`CrashLoopBackOff`).
- **Severity**: Critical (Deployment rollout blocked).
- **Impact**: New application pods failed to reach the `Ready` state, preventing successful rollout.
- **Symptoms**: Pod status showing `CrashLoopBackOff` with restart count increasing every few seconds.
- **Investigation**:
  1. Checked pod status via `kubectl get pods`, confirming `0/1 Ready` and `CrashLoopBackOff`.
  2. Extracted application logs from failed attempt using `kubectl logs <pod-name> --previous`.
  3. Identified `sqlite3.OperationalError` due to unwriteable path specified in `DATABASE_URL`.
- **Root Cause**: Invalid environment variable configuration (`DATABASE_URL="invalid_path:///invalid/db.sqlite"`) pointing to a non-existent directory.
- **Resolution**: Updated deployment environment variable back to valid path `sqlite:////app/instance/database.db`.
- **Validation**: Observed rolling update complete, new pods reached `1/1 Ready`, and `/health` returned HTTP 200.

### Formal 5 Whys Root Cause Analysis (RCA 1/5)
1. **Why did the Pod crash?** The Flask application threw an unhandled exception during startup sequence.
2. **Why was an exception thrown?** SQLAlchemy failed to connect/initialize the SQLite database file.
3. **Why did database initialization fail?** The application attempted to create a database file in `/invalid/db.sqlite`, a non-existent path.
4. **Why was the wrong path supplied?** An incorrect `DATABASE_URL` environment variable was applied to the Deployment manifest.
5. **Root Cause**: Absence of automated environment variable schema validation prior to applying deployment changes.
- **Preventive Action**: Implement pre-deployment manifest linting and staging health tests.

---

## Incident: INC-003 (ImagePullBackOff)
- **Summary**: Pods failed to start following a deployment update due to container image pull failures[cite: 3].
- **Severity**: High (Deployment rollout stalled)[cite: 3].
- **Impact**: New replicas could not be scheduled or started, leaving deployment in a degraded state[cite: 3].
- **Symptoms**: Pod status displayed `ErrImagePull` transitioning to `ImagePullBackOff`[cite: 3].
- **Investigation**:
  1. Inspected pod states via `kubectl get pods`, noticing `0/1 ContainerCreating` and `ImagePullBackOff`[cite: 3].
  2. Executed `kubectl describe pod` to inspect events[cite: 3].
  3. Located event error: `Failed to pull image "student-api:v9.9.9-nonexistent": rpc error: code = Unknown desc = Error response from daemon: manifest unknown`[cite: 3].
- **Root Cause**: Deployment manifest was updated with an invalid/non-existent container image tag (`v9.9.9-nonexistent`)[cite: 3].
- **Resolution**: Executed `kubectl rollout undo deployment/student-api` to revert to the last working revision (`student-api:1.0` or `1.1`)[cite: 3].
- **Validation**: Confirmed old revision pods resumed `1/1 Ready` status and application `/health` checks succeeded[cite: 3].

### Formal 5 Whys Root Cause Analysis (RCA 2/5)
1. **Why did the Pod fail to start?** The container runtime could not pull the required image layer[cite: 3].
2. **Why could the runtime not pull the image?** The registry responded that the requested tag did not exist[cite: 3].
3. **Why was a non-existent tag requested?** An incorrect image tag string was specified during the `kubectl set image` command[cite: 3].
4. **Why was the tag not verified before deployment?** Image tag verification was not automated in the deployment pipeline[cite: 3].
5. **Root Cause**: Lack of automated CI/CD image tag existence check and release management guardrails[cite: 3].
- **Preventive Action**: Implement CI/CD pipelines that validate Docker registry image tags prior to running deployment apply commands[cite: 3].

---

## Incident: INC-004 (Service Has No Endpoints)
- **Summary**: Service failed to route traffic to active application Pods due to a selector label mismatch[cite: 3].
- **Severity**: High (Application completely unreachable via Service/Ingress)[cite: 3].
- **Impact**: All HTTP requests returned `502 Bad Gateway` or `503 Service Unavailable` errors[cite: 3].
- **Symptoms**: `kubectl get endpoints student-api-svc` displayed `<none>`[cite: 3].
- **Investigation**:
  1. Verified Pod status using `kubectl get pods -n student-platform`, confirming pods were `1/1 Ready`[cite: 3].
  2. Inspected Service configuration using `kubectl describe svc student-api-svc`[cite: 3].
  3. Identified mismatch between `spec.selector` (`app=wrong-app`) and Pod labels (`app=student-api`)[cite: 3].
- **Root Cause**: Misconfigured Service label selector preventing Kubernetes endpoint controller from populating target Pod IPs[cite: 3].
- **Resolution**: Updated `spec.selector.app` to match Pod template label `student-api` using `kubectl patch`[cite: 3].
- **Validation**: Confirmed endpoint IP assignment (`kubectl get ep`) and validated HTTP 200 response from `/health`[cite: 3].

### Formal 5 Whys Root Cause Analysis (RCA 3/5)
1. **Why did clients receive HTTP 502/503 errors?** The Ingress Controller could not proxy requests to any backend Pod[cite: 3].
2. **Why could Ingress not route to any backend?** The targeted Kubernetes Service contained 0 registered Endpoints[cite: 3].
3. **Why were there no Service Endpoints?** The Service selector did not match the labels defined on running application Pods[cite: 3].
4. **Why did the selector mismatch occur?** Manual/unvalidated YAML modifications altered selector keys without cross-checking Deployment metadata[cite: 3].
5. **Root Cause**: Absence of automated Kubernetes manifest validation/linter to enforce label consistency across Deployment and Service resources[cite: 3].
- **Preventive Action**: Integrate `kube-linter` or Helm charts to strictly bind Service selectors to Deployment label templates[cite: 3].

---

## Incident: INC-005 (Ingress Traffic Routing Failure)
- **Summary**: External HTTP requests to `localhost:80` failed to reach the Ingress Controller.
- **Severity**: Medium (Internal cluster routing functional, external access boundary blocked)[cite: 3].
- **Impact**: Developers and external automated tests could not query `/health` or application endpoints[cite: 3].
- **Symptoms**: Connection error `curl: (7) Failed to connect to localhost port 80`[cite: 3].
- **Investigation**:
  1. Inspected `ingress-nginx` namespace services[cite: 3].
  2. Verified Ingress resource rules using `kubectl get ingress -n student-platform`[cite: 3].
  3. Identified that local host port `80` was not directly mapped to the Kind node interface[cite: 3].
- **Root Cause**: Missing local port-forward or NodePort binding between the host networking loopback interface and the `ingress-nginx-controller` service[cite: 3].
- **Resolution**: Port-forwarded host port `8080` to `ingress-nginx-controller` port `80` using `kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80`[cite: 3].
- **Validation**: Executed `curl -i -H "Host: student-api.local" http://localhost:8080/health`, receiving `HTTP 200 OK`[cite: 3].

### Formal 5 Whys Root Cause Analysis (RCA 4/5)
1. **Why did the curl request fail?** Host OS could not establish a TCP connection on port `80`[cite: 3].
2. **Why was port 80 unresponsive?** No host process or container daemon was bound to `localhost:80`[cite: 3].
3. **Why was the Ingress controller not listening on host port 80?** The Kind cluster configuration was set up without hostPort mappings for standard HTTP[cite: 3].
4. **Why was hostPort missing?** Default Kind cluster deployment was initialized with basic NodePort settings[cite: 3].
5. **Root Cause**: Discrepancy between environment deployment architecture (Kind NodePort) and local client access assumptions[cite: 3].
- **Preventive Action**: Document explicitly in the runbook to run `kubectl port-forward` for local testing or configure Kind extraPortMappings on cluster creation[cite: 3].

---

## Incident: INC-005 (Ingress Traffic Routing Failure)
- **Summary**: External HTTP requests to `localhost:80` failed to reach the Ingress Controller.
- **Severity**: Medium (Internal cluster routing functional, external access boundary blocked)[cite: 3].
- **Impact**: Developers and external automated tests could not query `/health` or application endpoints[cite: 3].
- **Symptoms**: Connection error `curl: (7) Failed to connect to localhost port 80`[cite: 3].
- **Investigation**:
  1. Inspected `ingress-nginx` namespace services[cite: 3].
  2. Verified Ingress resource rules using `kubectl get ingress -n student-platform`[cite: 3].
  3. Identified that local host port `80` was not directly mapped to the Kind node interface[cite: 3].
- **Root Cause**: Missing local port-forward or NodePort binding between the host networking loopback interface and the `ingress-nginx-controller` service[cite: 3].
- **Resolution**: Port-forwarded host port `8080` to `ingress-nginx-controller` port `80` using `kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80`[cite: 3].
- **Validation**: Executed `curl -i -H "Host: student-api.local" http://localhost:8080/health`, receiving `HTTP 200 OK`[cite: 3].

### Formal 5 Whys Root Cause Analysis (RCA 4/5)
1. **Why did the curl request fail?** Host OS could not establish a TCP connection on port `80`[cite: 3].
2. **Why was port 80 unresponsive?** No host process or container daemon was bound to `localhost:80`[cite: 3].
3. **Why was the Ingress controller not listening on host port 80?** The Kind cluster configuration was set up without hostPort mappings for standard HTTP[cite: 3].
4. **Why was hostPort missing?** Default Kind cluster deployment was initialized with basic NodePort settings[cite: 3].
5. **Root Cause**: Discrepancy between environment deployment architecture (Kind NodePort) and local client access assumptions[cite: 3].
- **Preventive Action**: Document explicitly in the runbook to run `kubectl port-forward` for local testing or configure Kind extraPortMappings on cluster creation[cite: 3].

---

## Incident: INC-006 (Readiness Probe Failure)
- **Summary**: Pods remained stuck in `0/1 Ready` state despite the application container running.
- **Severity**: High (Pods excluded from Service endpoints, blocking traffic).
- **Impact**: Ingress returned HTTP 503 as no ready endpoints were available to serve traffic.
- **Symptoms**: `kubectl get pods` displayed `STATUS: Running` but `READY: 0/1`.
- **Investigation**:
  1. Ran `kubectl describe pod` and checked the `Events` section.
  2. Observed event: `Readiness probe failed: HTTP probe failed with statuscode: 404`.
  3. Inspected deployment manifest and found `readinessProbe.httpGet.path` configured to `/nonexistent-health` instead of `/health`.
- **Root Cause**: Misconfigured Readiness Probe URI path causing HTTP 404 responses during readiness checks.
- **Resolution**: Updated `readinessProbe.httpGet.path` to `/health` in the Deployment spec.
- **Validation**: Observed Pods transitioning to `1/1 Ready` and endpoints populated in `student-api-svc`.

### Formal 5 Whys Root Cause Analysis (RCA 5/5)
1. **Why was traffic not routed to the Pod?** The Pod failed its Readiness Probe checks.
2. **Why did the Readiness Probe fail?** The probe endpoint returned a `404 Not Found` response.
3. **Why did it return 404?** Kubernetes probed `/nonexistent-health`, which is not exposed by the Flask app.
4. **Why was the wrong path configured?** Typo introduced in the deployment manifest during a configuration update.
5. **Root Cause**: Lack of automated schema and endpoint contract testing before applying Kubernetes manifests.
- **Preventive Action**: Implement manifest validation tests in CI/CD pipeline to verify probe endpoints against OpenAPI/Swagger specs.

---

## Incident: INC-007 (Resource Quota / OOMKilled Error)
- **Summary**: Application container terminated abruptly due to exceeding memory limits.
- **Severity**: High (Intermittent application downtime and restart spikes).
- **Impact**: Active user requests dropped when container was killed by Linux OOM killer.
- **Symptoms**: Pod status showed `OOMKilled` with exit code `137`.
- **Investigation**:
  1. Ran `kubectl describe pod` and inspected `Last State`.
  2. Found `Terminated: OOMKilled (Exit Code 137)`.
  3. Checked `resources.limits.memory` which was set too low (e.g., `16Mi`) for Python/Flask runtime startup requirements.
- **Root Cause**: Memory limit configured below the baseline operational threshold of the application runtime.
- **Resolution**: Increased `resources.limits.memory` to `128Mi` and `requests.memory` to `64Mi` in Deployment manifest.
- **Validation**: Monitored Pods with `kubectl top pods` and confirmed stable execution without restarts.

---

## Incident: INC-008 (ConfigMap / Secret Missing Dependency)
- **Summary**: Pod stuck in `CreateContainerConfigError` or `ContainerCreating` state.
- **Severity**: Critical (New Pods unable to launch).
- **Impact**: Deployment rollouts completely blocked; scaling actions failed.
- **Symptoms**: `kubectl get pods` showed status `CreateContainerConfigError`.
- **Investigation**:
  1. Executed `kubectl describe pod` to view failure details.
  2. Found event message: `configmap "api-config" not found`.
  3. Inspected environment variables in Deployment referencing a non-existent ConfigMap key/resource.
- **Root Cause**: Deployment manifest referenced a ConfigMap/Secret dependency that had not been created in the namespace.
- **Resolution**: Created the missing ConfigMap using `kubectl create configmap api-config --from-literal=...`.
- **Validation**: Kubernetes successfully created the container and Pod status moved to `1/1 Ready`.

---

## Incident: INC-009 (Database Connection Timeout / Connection Pool Exhaustion)
- **Summary**: Student API endpoint returned `HTTP 500 Internal Server Error` due to database connection failures.
- **Severity**: Critical (High impact on user write/read operations).
- **Impact**: API requests involving database operations failed under elevated traffic.
- **Symptoms**: Application logs showed `sqlite3.OperationalError: database is locked` or connection timeout exceptions.
- **Investigation**:
  1. Inspected application logs via `kubectl logs -n student-platform -l app=student-api`.
  2. Identified bottleneck caused by SQLite file locks under concurrent connections.
  3. Checked application connection pool settings and persistent volume lock behaviors.
- **Root Cause**: SQLite concurrency limitations during multi-replica deployment access to a shared or local database file.
- **Resolution**: Scaled replicas down temporarily to avoid file locking conflicts and updated connection pool handling.
- **Validation**: Re-tested API endpoints (`/students`) with concurrent requests; response status returned `200 OK`.

---

## Incident: INC-010 (RBAC / ServiceAccount Permission Denied)
- **Summary**: Internal background job or service failed to interact with Kubernetes API server.
- **Severity**: Medium (Internal metrics/cluster interaction blocked).
- **Impact**: Microservices requiring API access received `403 Forbidden` responses.
- **Symptoms**: Pod logs displayed `User "system:serviceaccount:student-platform:default" cannot list resource "pods"`.
- **Investigation**:
  1. Checked service account assigned to the deployment (`spec.template.spec.serviceAccountName`).
  2. Inspected Role / ClusterRole bindings in `student-platform` namespace.
  3. Found default ServiceAccount lacked required `get` and `list` verbs for cluster resources.
- **Root Cause**: Missing dedicated ServiceAccount with bound Role/RoleBinding rules for Kubernetes API access.
- **Resolution**: Created custom `ServiceAccount` and bound it to a `Role` with explicit resource verbs.
- **Validation**: Application pod restarted; authorization errors vanished from pod logs.

---

## Incident: INC-011 (PVC Storage Full / Disk Pressure)
- **Summary**: Application failed to append new records or write database log entries.
- **Severity**: High (Application write features degraded).
- **Impact**: Database writes failed and Pods were marked for eviction due to node disk pressure.
- **Symptoms**: Pod events showed `DiskPressure` and application logs reported `IOError: [Errno 28] No space left on device`.
- **Investigation**:
  1. Ran `kubectl get pvc -n student-platform` to inspect claim status.
  2. Executed `df -h` inside container via `kubectl exec` to check disk usage.
  3. Identified persistent volume capacity reached 100% due to uncleaned logs and SQLite growth.
- **Root Cause**: Insufficient storage volume allocation and lack of log rotation policy.
- **Resolution**: Expanded PersistentVolumeClaim size and purged temporary log files.
- **Validation**: Storage usage dropped below threshold and write operations resumed successfully.

---

## Incident: INC-012 (Network Policy Ingress/Egress Blocked)
- **Summary**: Pods within `student-platform` namespace could not communicate with internal services.
- **Severity**: High (Internal network isolation breaking service dependency).
- **Impact**: Traffic between Ingress controller / Frontend and Backend Pods was completely dropped.
- **Symptoms**: Inter-service HTTP requests timed out (`Connection timed out`).
- **Investigation**:
  1. Tested cross-pod connectivity using `kubectl exec -it <pod> -- curl <service-ip>`.
  2. Checked NetworkPolicies in namespace using `kubectl get networkpolicy -n student-platform`.
  3. Discovered active restrictive default-deny NetworkPolicy blocking traffic on port `5001`.
- **Root Cause**: Overly strict NetworkPolicy rule without explicit ingress permission for port `5001`.
- **Resolution**: Applied updated NetworkPolicy allowing ingress traffic from Ingress controller namespace on target ports.
- **Validation**: Executed curl test across pods; connectivity restored with HTTP 200 responses.
