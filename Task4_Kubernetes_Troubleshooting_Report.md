# Task 4: Kubernetes Troubleshooting Report (RCA)

## Challenge A: CrashLoopBackOff (Application/Container Startup Failure)
- **Symptom**: Pod enters `CrashLoopBackOff` state.
- **Root Cause**: Invalid container startup command or missing entrypoint script.
- **Diagnostic Step**: `kubectl logs -n student-platform <pod-name>` showed script execution errors.
- **Resolution**: Reverted the startup command in `deployment.yaml` to default python execution.

## Challenge B: ImagePullBackOff (Platform/Registry Failure)
- **Symptom**: Pod stuck in `ErrImagePull` / `ImagePullBackOff`.
- **Root Cause**: Deployment referenced non-existent image tag `student-api:invalid-tag-xyz`.
- **Diagnostic Step**: `kubectl describe pod -n student-platform <pod-name>` showed failed image pull events.
- **Resolution**: Executed `kubectl rollout undo deployment/student-api -n student-platform` to rollback to stable image version.

## Challenge C: Service Has No Endpoints (Networking Failure)
- **Symptom**: Service endpoint returned empty list `<none>` and requests failed with 503/timeout.
- **Root Cause**: Mismatched label selector (`app=wrong-app-label`) in Service specification.
- **Diagnostic Step**: `kubectl get endpoints student-api-svc -n student-platform` showed `<none>`.
- **Resolution**: Patched service selector back to `app=student-api`.

## Challenge D: Readiness Probe Failure (Health Check Failure)
- **Symptom**: Pod status remained `Running` but `0/1 READY`.
- **Root Cause**: Readiness probe pointed to unreachable port `9999`.
- **Diagnostic Step**: `kubectl describe pod -n student-platform <pod-name>` logged Readiness probe failure HTTP connection errors.
- **Resolution**: Restored readiness probe port to `5001`.
