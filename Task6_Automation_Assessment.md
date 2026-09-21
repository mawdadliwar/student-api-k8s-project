# Task 6: Automation Assessment Report

## 1. Executive Summary
This document reviews the manual operational activities performed in Task 5 for the Student Management Platform and identifies opportunities for infrastructure provisioning automation (via Terraform) and configuration management automation (via Ansible)[cite: 2].

---

## 2. Manual Activities vs. Automated Target Matrix

| Activity | Current State | Tool Used | Target State | Target Tool | Rationale for Automation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cluster Provisioning** | Manual | Kind | Automated | Shell / Terraform | Ensures repeatable local Kubernetes cluster environment setup[cite: 2]. |
| **Namespace Creation** | Manual | kubectl | Automated | Terraform | Declarative definition of environment scope and isolated resources[cite: 2]. |
| **Deploy App Manifests** | Manual | kubectl | Automated | Terraform / Ansible | Prevents manual `kubectl apply` drift and human syntax errors[cite: 2]. |
| **ConfigMap & Secret** | Manual | kubectl | Automated | Terraform | Centralizes environmental variables and sensitive credentials declaratively[cite: 2]. |
| **PVC Management** | Manual | kubectl | Automated | Terraform | Guarantees exact volume configuration and storage binding persistence[cite: 2]. |
| **App Health Verification**| Manual | curl / kubectl| Automated | Ansible | Provides instant automated operational readiness checks and status reports[cite: 2]. |
| **Log Collection** | Manual | kubectl logs | Semi-Automated| Ansible | Automates diagnostic log fetching during incident responses[cite: 2]. |
| **Database Backup/Restore**| Manual | sqlite3 / cp | Automated | Ansible | Eliminates manual copy operations for SQLite database persistence handling[cite: 2]. |
| **Scaling Workloads** | Manual | kubectl scale| Automated | Terraform / Ansible | Configurable replica counts managed via code/variables[cite: 2]. |

---

## 3. Tool Responsibilities Strategy
* **Terraform**: Handles desired infrastructure state creation (`Namespace`, `Deployment`, `Service`, `ConfigMap`, `Secret`, `PVC`)[cite: 2].
* **Ansible**: Handles operational configuration, post-deployment health verification, log extractions, and automated rollbacks[cite: 2].
