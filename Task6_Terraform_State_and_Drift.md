# Task 6: Terraform State & Configuration Drift Report

## 1. Understanding Terraform State
* **What is State?**: A JSON file (`terraform.tfstate`) that maps declarative resource configurations to real-world infrastructure objects.
* **Why Required?**: It tracks metadata, manages resource dependencies, improves execution performance, and provides source-of-truth mapping[cite: 2].
* **Manual Manipulation Hazard**: Deleting or manually editing the state file causes loss of target context, leading to duplicate creation or orphan resources[cite: 2].

---

## 2. Configuration Drift Demonstration
To simulate and observe state drift[cite: 2]:
1. **Initial Deployment**: Provisioned `student-api` deployment with `replicas = 2` via Terraform[cite: 2].
2. **Manual Intervention**: Executed `kubectl scale deployment/student-api --replicas=5 -n student-platform-tf` directly via CLI[cite: 2].
3. **Drift Detection**: Executing `terraform plan` identified a discrepancy between declared state (2) and active cluster state (5)[cite: 2].
4. **Reconciliation**: Running `terraform apply` safely restored cluster state back to the declared `2` replicas, resolving the drift[cite: 2].

---

## 3. Data Persistence Analysis (SQLite vs Production Storage)
1. **SQLite Storage Location**: Stored inside the mounted PVC path (`/app/data/students.db`)[cite: 2].
2. **Deployment Lifecycle Impact**: Deleting/recreating Pods or Deployments retains existing database records because the claim is detached and reattached[cite: 2].
3. **PVC Lifecycle Risk**: Running `terraform destroy` purges the PVC resource, completely deleting the underlying volume and losing data[cite: 2].
4. **Production Alternative**: For production topologies, managed stateful databases (e.g., PostgreSQL/RDS with automated backups) must be used instead of embedded local volumes[cite: 2].
