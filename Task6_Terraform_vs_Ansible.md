# Task 6: Infrastructure vs Configuration Management (Terraform vs Ansible)

## Questions & Architectural Answers

### Q1: When should Terraform be used?
* **Answer**: For declarative infrastructure provisioning (e.g., Kubernetes namespaces, deployments, services, cloud VMs, networking, PVCs). It focuses on defining "what infrastructure should exist".

### Q2: When should Ansible be used?
* **Answer**: For configuration management, server orchestration, application deployments, continuous health checks, automated operational maintenance, and log/backup extractions. It focuses on "how to configure existing systems".

### Q3: Can Terraform configure an operating system?
* **Answer**: While Terraform can execute basic shell scripts via local-exec or remote-exec provisioners, it lacks native configuration management capabilities like package management, idempotent service configs, and complex templating.

### Q4: Can Ansible provision infrastructure?
* **Answer**: Yes, through cloud modules or Kubernetes collections, but it is procedural rather than state-declarative. It does not maintain a state file to track infrastructural graph dependencies like Terraform does.

### Q5: What happens if infrastructure changes outside Terraform?
* **Answer**: Configuration Drift occurs. Running `terraform plan` will detect discrepancies between real-world infrastructure and the recorded `.tfstate` file, prompting Terraform to apply fixes and restore state.

### Q6: Why is idempotency important?
* **Answer**: Idempotency guarantees that executing automation multiple times produces the same desired target state without causing unintended modifications or duplicate resources.

### Q7: Why should infrastructure and configuration be separated?
* **Answer**: To maintain modularity, enforce clear operational boundaries, reduce failure blast radiuses, and allow independent lifecycle management of platform topology vs runtime applications.

### Q8: How could Terraform and Ansible work together in production?
* **Answer**: Terraform provisions the base cloud/Kubernetes resources, writes state outputs, and hands off dynamic endpoints to Ansible playbooks to handle application deployments, configuration templates, and day-2 operations.
