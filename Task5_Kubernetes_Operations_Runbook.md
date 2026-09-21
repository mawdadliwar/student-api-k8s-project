## 1. Daily Health-Check Procedure
Execute the following verification flow top-down:

1. **Cluster & Node Health**:
   ```bash
   kubectl get nodes -o wide
   kubectl top nodes
