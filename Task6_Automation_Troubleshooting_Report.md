# Task 6: Automation Failure & Troubleshooting Incident Report

## Incident Matrix Overview

| Incident ID | Target Tool | Failure Scenario | Failure Category | Status |
| :--- | :--- | :--- | :--- | :--- |
| **INC-01** | Terraform | Invalid HCL Syntax | Configuration Error | RESOLVED |
| **INC-02** | Terraform | Resource Naming Conflict | State Discrepancy | RESOLVED |
| **INC-03** | Terraform | Active Manual Replicas Scale | Configuration Drift | RESOLVED |
| **INC-04** | Ansible | Python `kubernetes` Library Missing | Environment Dependency | RESOLVED |
| **INC-05** | Ansible | Invalid Docker Container Tag | Deployment Rollout Failure | RESOLVED |

---

## Detailed Failure Analysis

### Incident INC-01: Terraform Syntax Error
* **Scenario**: Introduced syntax error in `modules/kubernetes/main.tf`.
* **Impact**: Prevented execution plan generation.
* **Investigation & Resolution**: `terraform validate` flagged line error; corrected closing brackets.

### Incident INC-02: Kubernetes Resource Conflict
* **Scenario**: Applied Terraform manifests while existing Kubernetes deployment already existed in cluster.
* **Impact**: Terraform `apply` failed with `deployments.apps "student-api" already exists`.
* **Investigation & Resolution**: Purged orphaned namespace via `kubectl delete namespace student-platform-tf` and re-executed `terraform apply`.

### Incident INC-03: Configuration Drift
* **Scenario**: Manually scaled replicas to `5` via `kubectl scale`.
* **Impact**: Unmanaged state drift in production workload.
* **Investigation & Resolution**: Executed `terraform plan` to detect drift; ran `terraform apply` to enforce declared state back to `2` replicas.

### Incident INC-04: Missing Python Dependency
* **Scenario**: Executed Ansible Kubernetes modules without python-kubernetes library installed.
* **Impact**: Playbook failed immediately with module import error.
* **Investigation & Resolution**: Installed required system bindings via `sudo apt install python3-kubernetes`.

### Incident INC-05: Non-existent Container Image Deployment
* **Scenario**: Deployed invalid tag `student-api:invalid-v99` via Ansible deployment playbook.
* **Impact**: Pod stuck in `ImagePullBackOff` phase.
* **Investigation & Resolution**: Ansible rescue block triggered `kubectl rollout undo` automatically, safely reverting workload back to functional revision.
