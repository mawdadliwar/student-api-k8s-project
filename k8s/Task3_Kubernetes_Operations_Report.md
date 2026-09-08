# Task 3 — Kubernetes Operations Report

**Status:** Complete
**Project:** Student Management API — Local Kubernetes Infrastructure & Cluster Preparation
**Date:** September 8, 2026

---

## 1. Environment Overview

| Item | Detail |
|---|---|
| Host OS | Ubuntu (native install, dual boot — **not** a VM, **not** Windows/WSL2) |
| Hardware | AMD Ryzen 5 3500U, 8 CPU cores, ~5.7GB RAM (4GB swap) |
| Disk | 39GB root partition, single-digit GB free — required active space management (see §10) |
| Container runtime (host) | Docker Engine (already installed/used in Task 2) |
| kubectl | v1.36.3 (already installed before this task started) |

Because the workstation runs Ubuntu natively rather than Windows, the WSL2 and Docker Desktop layers described in the task template were not required. Docker Engine and the Kubernetes distribution run directly on the Linux kernel, which is functionally closer to a real production Linux host than a Windows + WSL2 + Docker Desktop stack would be.

---

## 2. Kubernetes Distribution Selection

**Selected: Kind (Kubernetes IN Docker)**

**Reasoning:**
- Kind runs each cluster node as a Docker **container**, not a full virtual machine. On a machine with only ~5.7GB RAM, this is significantly lighter than alternatives (e.g., minikube's VM-driver mode).
- Kind has first-class support for multi-node clusters (control-plane + multiple workers) defined in a single declarative config file.
- Kind is fast to create/tear down, which suits an iterative training/local environment.

**Alternatives considered:**
- **minikube** — more feature-rich (built-in addons, dashboard) but heavier on resources when using a VM driver; rejected primarily due to RAM constraints.
- **k3d** (k3s in Docker) — also lightweight and viable, but Kind was chosen for its wider adoption in CI/testing contexts and closer alignment with upstream Kubernetes conformance testing.

---

## 3. Installation

Installed the `kind` binary directly (no package manager) on Linux:

```bash
curl -4 -Lo ./kind https://github.com/kubernetes-sigs/kind/releases/download/v0.30.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

**Issue encountered:** The initial download attempt via `kind.sigs.k8s.io` hung indefinitely. Diagnosis with `curl -Iv` showed the workstation was attempting to connect over **IPv6** first, and IPv6 routes were unreachable on the local network (`Network is unreachable`). Two fixes were combined:
1. Forced IPv4 with the `-4` curl flag.
2. Downloaded directly from the GitHub Releases URL instead of the `kind.sigs.k8s.io` redirect domain.

Verified installation:
```bash
kind version
# kind v0.30.0 go1.24.6 linux/amd64
```

---

## 4. Cluster Creation

**Config file** (`k8s/kind-config.yaml`):
```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: student-platform
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

**Command:**
```bash
kind create cluster --config kind-config.yaml
```

**Result — Nodes:**

| Node | Role | Status | Version | Container Runtime | OS Image |
|---|---|---|---|---|---|
| student-platform-control-plane | control-plane | Ready | v1.34.0 | containerd://2.1.3 | Debian GNU/Linux 12 (bookworm) |
| student-platform-worker | worker | Ready | v1.34.0 | containerd://2.1.3 | Debian GNU/Linux 12 (bookworm) |
| student-platform-worker2 | worker | Ready | v1.34.0 | containerd://2.1.3 | Debian GNU/Linux 12 (bookworm) |

`kubectl config get-contexts` confirmed `kind-student-platform` was automatically set as the current context after cluster creation, alongside a pre-existing, unrelated `kubernetes-admin@kubernetes` context (not investigated further as it is not used by this project).

---

## 5. Namespace

Created the dedicated namespace `student-platform` for all project resources, first **imperatively**, then reconciled it **declaratively** via manifest — see §8 for the observation this produced.

```bash
kubectl create namespace student-platform
```
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: student-platform
```

Namespaces in this cluster are dedicated to keeping all future Student Management API resources isolated from Kubernetes system namespaces (`kube-system`, `kube-node-lease`, `kube-public`) and from any other project on the same cluster — useful for organization, clearer `kubectl` scoping, and (in a larger environment) access control and resource quotas per namespace.

---

## 6. Test Workload

Deployed a lightweight NGINX workload to validate that the cluster can schedule pods, pull images, run containers, and expose a Service — **before** deploying the real Student Management API in Task 4.

**`k8s/deployment.yaml`:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-test
  namespace: student-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx-test
  template:
    metadata:
      labels:
        app: nginx-test
    spec:
      containers:
        - name: nginx
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "100m"
              memory: "64Mi"
            limits:
              cpu: "250m"
              memory: "128Mi"
```

**`k8s/service.yaml`:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-test-svc
  namespace: student-platform
spec:
  type: ClusterIP
  selector:
    app: nginx-test
  ports:
    - port: 80
      targetPort: 80
```

`nginx:1.27-alpine` was chosen over `nginx:latest` specifically to minimize image size given the disk-space constraints described in §10.

Applied with:
```bash
kubectl apply -f namespace.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

**Verification:**
- Both pods reached `1/1 Running` (after a short `ContainerCreating` period while the image was pulled).
- Pods were scheduled one on `student-platform-worker`, one on `student-platform-worker2` — an even distribution across the available worker nodes.
- `kubectl logs` confirmed NGINX started cleanly with no errors.
- Service access was validated using `kubectl port-forward -n student-platform svc/nginx-test-svc 8080:80` from one terminal and `curl -v http://localhost:8080` from a second terminal, which returned `HTTP/1.1 200 OK` and the default NGINX welcome page.
  - *Troubleshooting note:* the first access attempt failed because `port-forward` (a blocking/foreground command) and `curl` were run in the same terminal session rather than two separate terminals — resolved once `curl` was run from a second terminal while `port-forward` remained active in the first.

---

## 7. Scaling

```bash
kubectl scale deployment nginx-test -n student-platform --replicas=4
```
Result: 2 new pods were created and scheduled — one onto `student-platform-worker`, one onto `student-platform-worker2` — bringing each worker to 2 pods for this Deployment. This even split across both workers is an early data point for the scheduling investigation (see §12): Kubernetes' default scheduler balances load across available, schedulable nodes rather than stacking all replicas on one node.

Scaled back down to the baseline:
```bash
kubectl scale deployment nginx-test -n student-platform --replicas=2
```

---

## 8. Declarative vs. Imperative — Observed in Practice

Creating the namespace imperatively (`kubectl create namespace`) and then applying an equivalent declarative manifest (`kubectl apply -f namespace.yaml`) produced this warning:

```
Warning: resource namespaces/student-platform is missing the
kubectl.kubernetes.io/last-applied-configuration annotation which is
required by kubectl apply. kubectl apply should only be used on
resources created declaratively by either kubectl create --save-config
or kubectl apply. The missing annotation will be patched automatically.
```

**Explanation:** `kubectl apply` tracks a resource's desired state via a `last-applied-configuration` annotation, which is only set automatically when a resource is first created *with* `apply` (or `create --save-config`). Because the namespace was first created imperatively, that annotation didn't exist yet; Kubernetes patched it in automatically on the first `apply`, and normal declarative management works from that point forward. This was a direct, hands-on illustration of why relying purely on imperative commands can create inconsistencies when a team later moves to a GitOps/declarative workflow.

---

## 9. Networking Investigation (Pod IP vs. Service IP)

**Objective:** understand Pod IP, Service IP, and Node IP behavior, and confirm empirically why a Service is required.

**Baseline (before test):**
- Pod `nginx-test-68c95448f9-r842m` — IP `10.244.2.2`, on `student-platform-worker2`
- Pod `nginx-test-68c95448f9-vwqz9` — IP `10.244.1.2`, on `student-platform-worker`
- Service `nginx-test-svc` — CLUSTER-IP `10.96.14.93`

**Test performed:**
```bash
kubectl delete pod nginx-test-68c95448f9-r842m -n student-platform
kubectl get pods -n student-platform -o wide
kubectl get svc -n student-platform
```

**Result:**
- The ReplicaSet immediately created a replacement pod to restore the desired replica count of 2: `nginx-test-68c95448f9-pqfpx`, again scheduled on `student-platform-worker2`.
- The replacement pod received a **new** IP: `10.244.2.4` (different from the deleted pod's `10.244.2.2`), even though it landed on the same node.
- The Service's CLUSTER-IP was **unchanged**: `10.96.14.93`.

**Findings:**

| Question | Answer |
|---|---|
| What happens when a Pod is deleted? | It is terminated and removed; since it's managed by a Deployment/ReplicaSet, a replacement Pod is created automatically to maintain the desired replica count. |
| Does the Pod IP remain the same? | No — Pod IPs are ephemeral and tied to the individual Pod's lifecycle. A new Pod gets a new IP even when rescheduled onto the same node. |
| Does the Service IP change? | No — the Service's ClusterIP is stable for the lifetime of the Service object, regardless of which Pods currently back it. |
| Why is a Service required? | Because Pod IPs are not reliable identifiers, a Service gives clients (or other Pods) one stable virtual IP/DNS name. Kubernetes continuously updates the Service's Endpoints to point at whichever healthy Pods currently match its label selector — the client never needs to track individual Pod IPs. |

**IP address types observed in this cluster:**
- **Pod IP** (e.g., `10.244.1.2`, `10.244.2.4`) — from the pod network (Kind's default CNI), routable between Pods across nodes, ephemeral per-Pod.
- **Service/Cluster IP** (e.g., `10.96.14.93`) — a stable virtual IP from the cluster's service CIDR, load-balances across all Pods matching the Service's selector, persists for the Service's lifetime.
- **Node IP** (e.g., `172.21.0.2` / `.3` / `.4`, from `kubectl get nodes -o wide`) — the address of each node container within Kind's Docker bridge network.

**Related operational note:** during this investigation, `kubectl get svc` and `kubectl delete pod` briefly returned an empty result / `NotFound` for resources that were confirmed to still exist seconds later. This is attributed to transient control-plane pressure from running a 3-node cluster on a ~5.7GB RAM host, not to actual data loss — see §10 for related resource constraints. Recommendation: avoid running kubectl commands from multiple terminal tabs against the same cluster simultaneously to reduce the chance of a confusing race between commands.

---

## 10. Disk Space Management (Operational Note)

The 39GB root partition proved to be a real operational constraint throughout this task, not just a documentation footnote:

| Point in time | Free space |
|---|---|
| Before cleanup | ~3.8GB |
| After `docker system prune -a` + removing an unrelated project image/container (`devops-task-manage-flask-app`) | ~4.6GB → ~6.5GB after further cleanup |
| After Kind cluster creation (3 node images pulled) | ~2.8GB |

This is being actively monitored; the cluster was deliberately not re-created unnecessarily during this task specifically to avoid repeatedly re-pulling multi-hundred-MB node images. `nginx:1.27-alpine` was selected as the test image for the same reason.

---

## 11. Resource Management

CPU and memory `requests` and `limits` were applied to the test workload (see the `resources` block in the Deployment manifest in §6):

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "64Mi"
  limits:
    cpu: "250m"
    memory: "128Mi"
```

- **Requests** guarantee a minimum amount of CPU/memory the scheduler reserves for the container on its assigned node — they directly influence scheduling decisions (a Pod will not be scheduled onto a node that cannot satisfy its requests).
- **Limits** cap the maximum CPU/memory a container may consume; exceeding the memory limit results in the container being OOMKilled, while exceeding the CPU limit results in throttling rather than termination.

Resource management matters in a shared cluster because, without requests/limits, a single misbehaving or resource-hungry Pod could starve other workloads on the same node — this becomes increasingly important once the real Student Management API and any supporting services are deployed in Task 4 alongside each other in the same namespace.

Verified with:
```bash
kubectl describe pod -n student-platform -l app=nginx-test
```
which confirmed the requests/limits were applied exactly as specified in the manifest.

---

## 12. Scheduling Investigation

**Objective:** understand how Kubernetes decides where to run a Pod, and document the actual distribution observed in this cluster.

### Node Capacity & Allocation

| Node | Role | CPU Requests | CPU Limits | Memory Requests | Memory Limits |
|---|---|---|---|---|---|
| student-platform-control-plane | control-plane | 950m (11%) | 100m (1%) | 290Mi (4%) | 390Mi (6%) |
| student-platform-worker | worker | 200m (2%) | 350m (4%) | 114Mi (1%) | 178Mi (3%) |
| student-platform-worker2 | worker | 200m (2%) | 350m (4%) | 114Mi (1%) | 178Mi (3%) |

`kubectl top nodes` returned `error: Metrics API not available` — expected in Kind, since `metrics-server` is not installed by default and requires a separate add-on. Documented in §14, Known Limitations.

### Pod Distribution (Observed)

| Pod | Node | Pod IP |
|---|---|---|
| nginx-test-...-vwqz9 | student-platform-worker | 10.244.1.2 |
| nginx-test-...-pqfpx | student-platform-worker2 | 10.244.2.4 |
| bad-image-app-...-twhqx | student-platform-worker | 10.244.1.4 |

Notably, the **control-plane node hosted no application Pods at all**. This is expected default behavior, not coincidence — control-plane nodes carry a `taint` (`node-role.kubernetes.io/control-plane:NoSchedule`) that prevents ordinary workloads from being scheduled onto them automatically, separating cluster-management resources from application-running resources.

This is consistent with the earlier scaling test (§7): after scaling to 4 replicas, Pods split evenly 2/2 between `worker` and `worker2`, with none scheduled on the control plane.

### How the Scheduler Decides (kube-scheduler)

The `kube-scheduler` component runs two phases for every new Pod requiring scheduling:

1. **Filtering** — eliminating any node that cannot host the Pod (insufficient resources, taints the Pod doesn't tolerate, unmet node-selector/affinity rules, etc.). In this cluster, the control plane was automatically excluded due to its taint.
2. **Scoring** — among the nodes that pass filtering, ranking them by criteria such as current load balance, and selecting the highest-scoring node.

### Findings

| Question | Answer |
|---|---|
| Were Pods evenly distributed? | Yes — a roughly even split between `worker` and `worker2`, with no stacking on a single node. |
| Did the control plane participate in scheduling? | No — automatically excluded by its default taint, consistent with the best practice of separating cluster management from application workloads. |
| Were there any obvious constraints affecting scheduling? | No — actual resource consumption was very low (under 15% CPU and memory on any node), giving the scheduler ample freedom to choose. |

### Lessons Learned
- Scheduling is not arbitrary — it follows two distinct phases (filtering, then scoring), which explains why the control plane consistently excluded itself across every test.
- The lack of `metrics-server` in Kind by default limits visibility into live resource usage (`top nodes/pods`). Instead, `kubectl describe nodes` (Allocated resources) was used to see reserved requests/limits, which is a useful but different signal from actual real-time usage.

---

## 13. Kubernetes Architecture Explanation

**Objective:** explain the role of each core Kubernetes component, tied to the actual cluster built in this task (`student-platform` — one control plane, two workers, via Kind).

### Overview

```
Kubernetes Cluster
 |
 +-------------------+-------------------+
 |                                       |
 Control Plane                    Worker Nodes
 (student-platform-control-plane)  (worker, worker2)
```

### Control Plane Components

**1. API Server (`kube-apiserver`)**
The single entry point for all interaction with the cluster — every `kubectl` command goes through it. It receives requests (create/get/patch/delete), validates them (authentication/authorization/validation), and persists the desired state to `etcd`. In this project, every command such as `kubectl apply -f deployment.yaml` or `kubectl patch svc` passed through the API Server before any actual execution occurred.

**2. Scheduler (`kube-scheduler`)**
Responsible for choosing which node a new Pod should run on (detailed in §12) via the Filtering → Scoring phases. It does not run the Pod itself — it only decides "who runs it" and records that decision through the API Server.

**3. Controller Manager (`kube-controller-manager`)**
A collection of control loops that continuously ensure the cluster's actual state matches its desired state. The clearest example observed hands-on: during the networking test (§9), when a Pod was deleted manually (`kubectl delete pod`), the ReplicaSet controller (part of the controller manager) detected that the actual Pod count had dropped below the desired replica count (2), and immediately created a replacement Pod with no manual intervention.

**4. etcd**
A distributed key-value store, and the single source of truth for the entire cluster's state — every object (Pods, Services, ConfigMaps, etc.) and its desired/actual state is stored here. Other components (Scheduler, Controller Manager) only read/write to it through the API Server — no other component talks to it directly.

### Worker Node Components

**1. kubelet**
The agent running on every worker node, taking instructions from the API Server about which Pods should run on that specific node. It's responsible for ensuring containers actually run as specified, and it's the component that reports the Events observed across all three incidents in the Troubleshooting Report (e.g. `CreateContainerConfigError`, `ErrImagePull`) — since it sits closest to the container's real-time state.

**2. Container Runtime**
The actual program responsible for running the containers. In this cluster (Kind on containerd), the runtime was `containerd://2.1.3` on all three nodes (as shown by `kubectl get nodes -o wide`). The kubelet communicates with it through the CRI (Container Runtime Interface) to pull images and start/stop containers.

**3. kube-proxy**
Responsible for implementing network rules (typically via iptables or IPVS) that route traffic sent to a Service's ClusterIP to the correct backing Pods. It updates these rules in real time as Endpoints change — this is what allowed, in §9, traffic to keep reaching the stable Service IP (`10.96.14.93`) with no interruption from the client's perspective, even after the backing Pod was deleted and replaced with a new IP.

**4. Pods**
The smallest schedulable unit in Kubernetes — one or more containers running together on the same node, sharing the same network namespace (same Pod IP). All Pods in this cluster were single-container (nginx, bad-image-app).

### How the Components Interacted in Practice

A concrete example from Incident 3 (Service Problem) summarizes the full interaction chain:
1. `kubectl apply -f broken-service.yaml` → sent to the **API Server** → persisted in **etcd**.
2. The **Endpoints controller** (part of the controller manager) attempted to match the selector against existing Pods — found no match, so it recorded empty Endpoints.
3. **kube-proxy** on each node had no network rules to update since there were no endpoints to begin with — the Service remained "alive" but pointing nowhere.
4. After the `kubectl patch` corrected the selector, the **Endpoints controller** detected the new match immediately, updated the Endpoints, and **kube-proxy** in turn updated its network rules — which is why the `curl` through `port-forward` returned `200 OK` right away.

This single example alone covers the interaction of: API Server + etcd + Controller Manager + kube-proxy + kubelet in one real sequence.

### Architecture Diagram

See the accompanying diagram, `Task3_Kubernetes_Architecture.svg`, which shows this same layering visually: Ubuntu host → Docker engine → Kind cluster (control plane + two worker nodes running test pods) → Service routing traffic to the pods.

---

## 14. Known Limitations & Recommendations

### Known Limitations

**1. Hardware constraints (RAM & CPU)**
The machine has only ~5.7GB RAM and 8 cores, which was the primary driver for choosing Kind (containers, not VMs) over heavier alternatives like minikube. Although actual resource utilization stayed low throughout the task (§12), running a full 3-node cluster on hardware this constrained leaves a small safety margin if real additional load is introduced.

**2. Disk space**
The 39GB root partition repeatedly dropped to critical levels (as low as ~2.8GB free) after pulling node images and test images (§10). This imposed real operational constraints: avoiding unnecessary cluster re-creation, and deliberately choosing lightweight images (`nginx:1.27-alpine` instead of `nginx:latest`).

**3. `metrics-server` not available**
Kind does not ship with `metrics-server` installed by default, so `kubectl top nodes/pods` is unavailable. `kubectl describe nodes` (Allocated resources) was used instead, which shows **reserved** requests/limits rather than **live** actual usage — an important distinction for documentation purposes.

**4. IPv6 connectivity issue**
Downloading the `kind` binary itself initially failed because the workstation attempted to connect over IPv6 on a network where IPv6 routes were unreachable (§3). Resolved by forcing IPv4 (`curl -4`) and downloading directly from GitHub Releases instead of the redirected domain.

**5. Transient API responsiveness under pressure**
`kubectl get svc` and `kubectl delete pod` were observed briefly returning empty results / `NotFound` for resources confirmed to still exist seconds later (§9) — attributed to transient control-plane pressure from running a 3-node cluster on a ~5.7GB RAM host, not actual data loss.

**6. Non-HA training environment (single control-plane)**
The cluster has only one control-plane node. This is appropriate for a local training/development environment, but does not represent a real production setup (which typically requires 3+ control-plane nodes for high availability). This limitation is expected and acceptable for the scope of this task.

**7. Native Linux instead of Windows/WSL2/Docker Desktop**
The task template assumed a Windows + WSL2 + Docker Desktop environment, but because the workstation runs Ubuntu natively (dual boot), the WSL2/Docker Desktop layer was skipped entirely — a documented deviation from the assumed environment, though (as noted in §1) arguably closer to a real production Linux host.

### Recommendations

- **Before moving to Task 4** (deploying the real application): install the `metrics-server` add-on so live resource monitoring is available before the real application takes on additional load.
- **Continuously monitor disk space** while deploying larger, real application images going forward — a periodic `docker system prune` or freeing additional space before starting Task 4 is recommended.
- **Avoid running kubectl commands from multiple terminal tabs simultaneously** against the same cluster, to reduce the chance of the race conditions observed in §9.
- **Document any change made via imperative commands** (such as `kubectl set image` or `kubectl patch`, used in Incidents 2 and 3 of the Troubleshooting Report) in the corresponding manifest files once troubleshooting concludes, so the declared (declarative) state stays in sync with the actual cluster state before any future `kubectl apply`.
- **If the project evolves toward a real production deployment**, consider moving to a multi-control-plane (HA) setup rather than relying on a single control-plane node, even though this is outside the scope of Task 3.

---

## Deliverables Summary

| Deliverable | Status | Location |
|---|---|---|
| 1. Kubernetes Cluster (control-plane + 2 workers, working kubectl, dedicated namespace) | ✅ Complete | Live cluster (`kind-student-platform` context) |
| 2. Kubernetes Manifests | ✅ Complete | `k8s/namespace.yaml`, `k8s/deployment.yaml`, `k8s/service.yaml` |
| 3. Cluster Architecture Diagram | ✅ Complete | `Task3_Kubernetes_Architecture.svg` |
| 4. Kubernetes Operations Report | ✅ Complete | This document |
| 5. Troubleshooting Report (3 incidents) | ✅ Complete | `Task3_Kubernetes_Troubleshooting_Report.md` |
| 6. Evidence (command outputs, node/pod/service state) | ✅ Complete | Embedded throughout this report and the Troubleshooting Report |

*This report reflects the completed state of Task 3.*
