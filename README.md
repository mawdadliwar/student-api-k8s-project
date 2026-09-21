# Student Management API - Dockerized

## Project Overview

A RESTful API for managing student records, prepared for operational readiness and Docker containerization.

The application uses Flask, SQLAlchemy, and SQLite. It can run directly with Python or inside a Docker container.

## Technology Stack

* Python 3.12
* Flask
* Flask-SQLAlchemy
* SQLAlchemy
* SQLite
* pytest
* Docker
* Docker Compose

## Project Structure

```text
StudentAPI/
├── app/
│   ├── models/
│   ├── routes/
│   ├── extensions.py
│   ├── config.py
│   └── __init__.py
├── instance/
├── tests/
├── Dockerfile
├── .dockerignore
├── compose.yaml
├── requirements.txt
├── run.py
├── .env
└── README.md
```

## Prerequisites

For Docker execution:

* Docker Engine
* Docker Compose

For local Python execution:

* Python 3.12 or compatible Python 3 version

The application dependencies do not need to be installed on the host when using Docker.

## Environment Variables

The application uses environment variables for runtime configuration.

Example `.env`:

```env
DATABASE_URL=sqlite:///database.db
PORT=5001
DEBUG=False
```

These values are passed to the container using:

```bash
--env-file .env
```

The Docker image can therefore be reused with different configuration values without rebuilding it.

## Running Locally

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
python run.py
```

The API will be available at:

```text
http://127.0.0.1:5001
```

## Dockerfile

The Dockerfile:

* Uses `python:3.12-slim`
* Installs dependencies from `requirements.txt`
* Copies only the required application files
* Uses `/app` as the working directory
* Runs the application as a non-root user
* Exposes port `5001`
* Configures a Docker health check
* Starts the API using `python run.py`

## .dockerignore

The following files and directories are excluded from the Docker build context:

```text
venv/
__pycache__/
*.pyc
.git/
.gitignore
.pytest_cache/
instance/
.env
```

Reasons for exclusion:

* `venv/` contains local Python packages that should be installed inside the image.
* Python cache files are unnecessary at runtime.
* `.git/` and `.gitignore` are source-control files and are not required by the application.
* `.pytest_cache/` contains temporary test information.
* `instance/` contains the local SQLite database and should instead be provided through persistent Docker storage.
* `.env` contains environment-specific configuration and should not be copied into the image.

## Build the Docker Image

Build version 1.0:

```bash
docker build -t student-api:1.0 .
```

Build version 1.1:

```bash
docker build -t student-api:1.1 .
```

List images:

```bash
docker images
```

The project contains both:

```text
student-api:1.0
student-api:1.1
```

## Run the Docker Container

Run the application with environment variables and persistent storage:

```bash
docker run -d \
  --name student-api-container \
  -p 5001:5001 \
  --env-file .env \
  -v student-api-data:/app/instance \
  student-api:1.0
```

The API is then available at:

```text
http://127.0.0.1:5001
```

## Health Check

Application health can be checked using:

```bash
curl http://127.0.0.1:5001/health
```

Expected response:

```json
{"database":"connected","status":"healthy"}
```

Docker health status can be checked using:

```bash
docker inspect --format='{{.State.Health.Status}}' student-api-container
```

A healthy container reports:

```text
healthy
```

## Container Logs

View logs:

```bash
docker logs student-api-container
```

Follow logs in real time:

```bash
docker logs -f student-api-container
```

## Container Lifecycle Operations

Start:

```bash
docker start student-api-container
```

Stop:

```bash
docker stop student-api-container
```

Restart:

```bash
docker restart student-api-container
```

Inspect:

```bash
docker inspect student-api-container
```

Execute a command inside the container:

```bash
docker exec -it student-api-container /bin/sh
```

Remove the container:

```bash
docker rm student-api-container
```

List all containers:

```bash
docker ps -a
```

## Docker Volume and Database Persistence

Create the volume:

```bash
docker volume create student-api-data
```

List volumes:

```bash
docker volume ls
```

The application database is stored using:

```text
student-api-data:/app/instance
```

The volume allows SQLite data to survive container removal and recreation.

## Docker Networking and Port Mapping

The application listens on container port:

```text
5001
```

The host exposes:

```text
5001
```

Port mapping:

```text
5001:5001
```

This means:

```text
Host Machine
127.0.0.1:5001
        ↓
Docker Port Mapping
        ↓
Container Port 5001
        ↓
Flask Application
```

The host port can be changed independently from the container port. For example:

```bash
docker run -p 5002:5001 student-api:1.1
```

In this case:

* Host Port = 5002
* Container Port = 5001

## Docker Compose

Start the application using Compose:

```bash
docker compose up -d --build
```

Check the service:

```bash
docker compose ps
```

Stop the Compose application:

```bash
docker compose down
```

View Compose logs:

```bash
docker compose logs
```

The Compose configuration includes:

* Application service
* Image/build configuration
* Port mapping
* Environment variables
* Persistent volume
* Health check
* Restart behavior

## API Endpoints

### Health

```text
GET /health
```

### Students

```text
GET /students
POST /students
GET /students/<id>
PUT /students/<id>
DELETE /students/<id>
```

## Image Versioning

The project uses versioned Docker images:

```text
student-api:1.0
student-api:1.1
```

Versioning makes it possible to identify deployments clearly and return to an earlier known version when a newer version introduces a problem.

## Security Considerations

The Docker image includes several basic security improvements:

* A slim Python base image is used to reduce image size.
* The application runs as a non-root user.
* Unnecessary local files are excluded using `.dockerignore`.
* The `.env` file is not copied into the image.
* Dependencies are installed from a pinned `requirements.txt`.

Remaining limitations include:

* Dependency vulnerability scanning has not been automated.
* The SQLite database is intended for this training environment rather than a production distributed database.
* Secrets should be managed with a dedicated secret-management mechanism in a real production environment.

## Troubleshooting

Three Docker troubleshooting scenarios were intentionally tested:

1. Incorrect host port mapping
2. Missing Python dependency/module
3. Container stopping because its main process exited

Each incident was investigated using Docker commands and container output, then resolved and validated.

## Docker Readiness

The application is ready for the next stage of the project: Local Kubernetes Infrastructure.

## Kubernetes Deployment (Task 4)

### Cluster Architecture
The Kubernetes deployment runs on a multi-node Kind cluster (student-platform) comprising 1 control-plane and 2 worker nodes. It uses an NGINX Ingress Controller to route HTTP traffic to a scalable Flask Deployment backed by SQLite stored on a Persistent Volume.

### Kubernetes Directory Structure
- k8s/pvc.yaml: PersistentVolumeClaim for SQLite database persistence
- k8s/deployment.yaml: Deployment specs (2 Replicas, Health Probes, Resources)
- k8s/service.yaml: ClusterIP Service pointing to app Pods
- k8s/ingress.yaml: NGINX Ingress rules mapping student-api.local

### Apply Kubernetes Manifests

1. Create target namespace:
   kubectl create namespace student-platform

2. Deploy Storage, Workload, and Service:
   kubectl apply -f k8s/pvc.yaml
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml

3. Deploy NGINX Ingress Controller & Resource:
   kubectl apply -f [https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml](https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml)
   kubectl apply -f k8s/ingress.yaml

### Accessing the Application

Add local domain mapping to /etc/hosts:
127.0.0.1 student-api.local

Execute API requests via Ingress Controller:
- Health endpoint: curl -H "Host: student-api.local" http://localhost:8080/health
- Get Students: curl -H "Host: student-api.local" http://localhost:8080/students

### Kubernetes Lifecycle & Operational Scenarios
- Rolling Updates: Zero-downtime rolling update executed from student-api:1.0 to student-api:1.1.
- Rollback Execution: Automated rollback via kubectl rollout undo upon deployment of bad image tag (1.2-broken).
- Root Cause Analysis (RCA): Tested and documented 4 failure scenarios:
  1. CrashLoopBackOff (Startup failure)
  2. ImagePullBackOff (Invalid image reference)
  3. Service with No Endpoints (Selector mismatch)
  4. Readiness Probe Failure (Mismatched probe port)

### Documentation Reports Included
- Task4_Kubernetes_Deployment_Report.md: Comprehensive setup and verification report.
- Task4_Kubernetes_Troubleshooting_Report.md: Root Cause Analysis for all 4 failure scenarios.
- ARCHITECTURE.txt: Visual ASCII text diagram of end-to-end data flow.
