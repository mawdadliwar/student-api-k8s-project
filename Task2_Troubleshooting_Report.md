# Task 2 — Docker Troubleshooting Report

## Overview

Three Docker troubleshooting scenarios were intentionally tested.

The purpose was to understand how to identify failures using Docker commands, logs, container status, and port configuration.

The three scenarios were:

1. Incorrect Port Mapping
2. Missing Module / Dependency Simulation
3. Container Stops Immediately

---

# Incident 1 — Incorrect Port Mapping

## Problem

The application listens on container port `5001`, but the container was intentionally started with the following incorrect host mapping:

```bash
docker run -d --name trouble-port -p 5002:5001 student-api:1.1
```

The objective was to demonstrate the difference between host and container ports.

---

## Symptoms

The container started successfully, but it was not available through the expected host port `5001`.

Docker showed:

```text
0.0.0.0:5002->5001/tcp
```

This means that the application was available through host port `5002`, not host port `5001`.

---

## Investigation

The container configuration was inspected using:

```bash
docker ps
```

The output showed:

```text
trouble-port
0.0.0.0:5002->5001/tcp
```

The application itself was healthy, which confirmed that the problem was not the Flask application.

The correct endpoint for the test container was:

```bash
curl http://127.0.0.1:5002/health
```

The health endpoint returned:

```json
{"database":"connected","status":"healthy"}
```

---

## Root Cause

The host port was mapped incorrectly.

The application listens on:

```text
Container Port = 5001
```

but the container was exposed on:

```text
Host Port = 5002
```

---

## Resolution

The temporary container was removed:

```bash
docker rm -f trouble-port
```

The application was then run with the correct mapping:

```text
5001:5001
```

---

## Validation

The application was successfully accessed through:

```bash
curl http://127.0.0.1:5001/health
```

Expected response:

```json
{"database":"connected","status":"healthy"}
```

---

## Lessons Learned

Docker port mapping follows the format:

```text
HOST_PORT:CONTAINER_PORT
```

Changing the host port does not change the port used by the application inside the container.

---

# Incident 2 — Missing Module / Dependency Simulation

## Problem

A missing Python module was intentionally simulated using:

```bash
docker run --name trouble-dependency student-api:1.1 python -c "import fake_package"
```

The purpose was to observe how Docker reports a Python dependency/module failure.

---

## Symptoms

The container command failed with:

```text
ModuleNotFoundError: No module named 'fake_package'
```

This demonstrates the type of runtime error that occurs when an application attempts to import a module that is not available in the environment.

---

## Investigation

The command was executed directly through Docker.

The error was:

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'fake_package'
```

The failure was therefore identified as a missing Python module.

---

## Root Cause

The requested module:

```text
fake_package
```

was not installed in the Docker environment.

---

## Resolution

The temporary troubleshooting container was removed:

```bash
docker rm trouble-dependency
```

The production image versions were not modified.

The existing application image remained available as:

```text
student-api:1.0
student-api:1.1
```

---

## Validation

The normal application image remained functional and was already verified using:

```bash
curl http://127.0.0.1:5001/health
```

with:

```json
{"database":"connected","status":"healthy"}
```

---

## Lessons Learned

Python import errors can be used to identify missing runtime modules.

Docker logs and command output provide direct evidence of application startup or runtime failures.

### Note

This incident intentionally simulated a missing module without modifying the project's `requirements.txt`. A full missing-dependency build test would remove an actual required dependency from the build process and rebuild the image. The current incident demonstrates the failure-diagnosis concept without altering the working application configuration.

---

# Incident 3 — Container Stops Immediately

## Problem

A container was intentionally started with a command that finishes immediately:

```bash
docker run --name trouble-stop student-api:1.1 python -c "print('Container finished')"
```

The purpose was to demonstrate the relationship between the container lifecycle and its main process.

---

## Symptoms

The command printed:

```text
Container finished
```

The container then stopped.

Docker showed:

```text
Exited (0)
```

---

## Investigation

The container status was checked using:

```bash
docker ps -a | grep trouble-stop
```

The result showed:

```text
Exited (0)
```

The logs were inspected using:

```bash
docker logs trouble-stop
```

The output was:

```text
Container finished
```

This confirmed that the main process completed successfully.

---

## Root Cause

A Docker container remains running while its main process is running.

In this test, the main process was:

```text
python -c "print('Container finished')"
```

The command completed immediately with exit code `0`.

Therefore Docker considered the container process finished and stopped the container.

---

## Resolution

The stopped troubleshooting container was removed using:

```bash
docker rm trouble-stop
```

The normal Student API container continues to use:

```text
python run.py
```

as its main process.

---

## Validation

The normal application container was verified through:

```bash
docker compose ps
```

and the health endpoint:

```bash
curl http://127.0.0.1:5001/health
```

The response was:

```json
{"database":"connected","status":"healthy"}
```

---

## Lessons Learned

A container is not a virtual machine.

The container lifecycle is directly related to the lifecycle of its main process.

If the main process exits, the container exits.

Therefore the application startup command is critical to keeping a service container running.

---

# Overall Troubleshooting Lessons

The troubleshooting exercises demonstrated three important operational concepts.

## Port Mapping

A correct container port does not automatically mean the application is reachable through every host port.

The mapping must be configured correctly:

```text
HOST_PORT:CONTAINER_PORT
```

## Application Dependencies

Python runtime modules must be available in the container environment.

Missing modules can be identified through Docker command output and application logs.

## Container Lifecycle

The container depends on its main process.

When the main process exits, the container exits as well.

---

# Troubleshooting Commands Used

The following Docker commands were used during troubleshooting:

```bash
docker run
docker ps
docker ps -a
docker logs
docker rm
docker rm -f
curl
```

These commands provide the basic operational tools required to identify, investigate, and resolve container problems.

# Conclusion

The required troubleshooting scenarios were intentionally introduced and investigated.

The observed failures were:

```text
Incident 1 → Incorrect Port Mapping
Incident 2 → Missing Module / Dependency Simulation
Incident 3 → Container Stops Immediately
```

Each incident was investigated using Docker status, configuration, command output, logs, or API validation.

The exercises improved understanding of Docker networking, runtime dependencies, and container lifecycle behavior.
