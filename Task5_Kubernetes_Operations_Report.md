# Task 5: Kubernetes Operations, Troubleshooting & Incident Management Report

## 1. Daily Operational Checks & Health Check Procedure
A systematic top-down methodology ensures operational visibility across all cluster tiers:

* **Cluster & Node Level**: Executing `kubectl get nodes -o wide` and `kubectl top nodes` verifies control-plane and worker readiness along with CPU/Memory saturation thresholds[cite: 1].
* **Namespace & Workload Level**: Executing `kubectl get all -n student-platform` checks Deployment availability and active Pod replica status[cite: 1].
* **Storage Tier**: Executing `kubectl get pvc,pv -n student-platform` ensures PersistentVolumeClaims remain bound[cite: 1].
* **Service & Ingress Layer**: Inspecting `kubectl get ingress,svc,ep -n student-platform` confirms proper Endpoint population and ingress rules[cite: 1].
* **Application Layer**: Verification via `curl -i -H "Host: student-api.local" http://localhost/health` validates end-to-end API responsiveness[cite: 1].

---

## 2. Application Availability Verification Procedure
To ensure full platform health, execute the following operational steps[cite: 1]:
1. **Cluster Health Check**: Confirm nodes are in `Ready` status[cite: 1].
2. **Workload Check**: Verify `student-api` Deployment has `2/2` desired replicas running[cite: 1].
3. **Endpoint Routing Check**: Confirm `student-api-svc` displays non-empty endpoints mapped to port `5001`[cite: 1].
4. **Ingress Reachability Check**: Send HTTP requests to Ingress host `student-api.local`[cite: 1].
5. **Functional Data Check**: Query `/students` endpoint to confirm database connectivity over the mounted SQLite PVC[cite: 1].

---

## 3. Scaling & Pod Lifecycle Operations
* **Scaling Dynamics**: Scaling replicas from 2 to 4 (`kubectl scale deployment/student-api --replicas=4`) triggers immediate ReplicaSet event scheduling[cite: 1]. The Kubernetes Scheduler distributes new Pods across available worker nodes (`student-platform-worker2`)[cite: 1]. Scaling down back to 2 sends `SIGTERM` signals for graceful termination[cite: 1].
* **Self-Healing Mechanics**: When a running Pod is manually deleted, the controlling ReplicaSet detects a drift between the current state (1) and desired state (2) and automatically spawns a replacement Pod without operator intervention[cite: 1].

---

## 4. Deployment Operations & Rollout Management
* **Zero-Downtime Rollouts**: Deployment updates follow a rolling update strategy, creating new Pods before terminating old ones to preserve availability[cite: 1].
* **Rollback Capabilities**: In the event of an invalid image tag or broken deployment, executing `kubectl rollout undo deployment/student-api` instantly reverts cluster state to the previous stable revision[cite: 1].

---

## 5. Kubernetes Troubleshooting Decision Guide: Logs vs. Events
Choosing the correct diagnostic tool speeds up Root Cause Analysis[cite: 1]:

| Operational Scenario | Diagnostic Tool | Primary Command |
| :--- | :--- | :--- |
| Container fails at startup or throws runtime exception | **Pod Logs** | `kubectl logs <pod-name> -n student-platform` |
| Container constantly restarts or crashes on launch | **Previous Container Logs** | `kubectl logs <pod-name> --previous` |
| Pod stuck in `Pending`, `ImagePullBackOff`, or `OOMKilled` | **Kubernetes Events** | `kubectl describe pod <pod-name>` |
| Traffic fails to reach backend Pods | **Endpoints / Service Info** | `kubectl get ep,svc -n student-platform` |

---

## 6. Incident Management Process & Severity Model

### Severity Classification Matrix
* **Critical (Sev-1)**: Total outage or database corruption with no workaround (e.g., INC-002 CrashLoopBackOff on all replicas, INC-009 Database locks)[cite: 1].
* **High (Sev-2)**: Functional degradation or deployment failure affecting redundancy (e.g., INC-003 ImagePullBackOff, INC-004 Missing Endpoints)[cite: 1].
* **Medium (Sev-3)**: External boundary routing issues with localized workaround available (e.g., INC-005 Ingress port forwarding requirement)[cite: 1].

---

## 7. Change vs. Incident Management
* **Incident**: An unplanned disruption or reduction in quality of an IT service (e.g., Pod crashing due to unhandled SQLite exception)[cite: 1].
* **Change**: A planned addition, modification, or removal of an authorized service or infrastructure component (e.g., increasing replica count from 2 to 4)[cite: 1].
* **Change-Induced Incidents**: A planned change can become an incident if modifications contain unvalidated environment variables, incorrect image tags, or mismatched Service selectors[cite: 1].

---

## 8. Root Cause Analysis (5-Whys) & Recovery Validation
Formal 5-Whys analysis was performed for major incidents to distinguish immediate causes from root architectural flaws[cite: 1]. Every incident resolution was validated across three tiers before sign-off[cite: 1]:
1. **Infrastructure**: Pod status `1/1 Ready`[cite: 1].
2. **Networking**: Valid Endpoint assignment in Service[cite: 1].
3. **Application**: HTTP `200 OK` response from `/health` and valid database queries[cite: 1].

---

## 9. Preventive Actions & Roadmap
To prevent recurrence of identified failure modes, the following improvements are scheduled for future automation tasks[cite: 1]:
* Integrate `kube-linter` in CI/CD pipelines to validate Deployment and Service label selectors[cite: 1].
* Implement automated container image tag validation before applying manifests[cite: 1].
* Define strict resource requests/limits and configure automated alerts for memory thresholds[cite: 1].
