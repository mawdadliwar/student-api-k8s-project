# Task 2 — Docker Operations Report

## 1. Docker Architecture Used

The Student Management Flask API was containerized using Docker.

The final architecture is:

```text
Host Machine
    |
    | HTTP Request
    v
Docker Runtime
    |
    +----------------------+
    | Student API Container|
    |                      |
    | Flask Application     |
    | Port 5001             |
    |                      |
    | SQLite Database       |
    +----------+-----------+
               |
               v
      Docker Named Volume
       student-api-data
```

The application runs inside a Docker container and communicates with the host through Docker port mapping.

The application uses SQLite for database storage and a Docker named volume for persistence.

---

## 2. Dockerfile Explanation

The Dockerfile uses the following base image:

```dockerfile
FROM python:3.12-slim
```

The slim Python image was selected to reduce the image size compared with a full Python image.

The working directory is:

```dockerfile
WORKDIR /app
```

Application dependencies are installed using:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

Only the required application files are copied:

```dockerfile
COPY app ./app
COPY run.py .
```

The container creates and uses a non-root user:

```dockerfile
RUN useradd -m appuser && \
    mkdir -p /app/instance && \
    chown -R appuser:appuser /app

USER appuser
```

This reduces the security risk of running the application as the root user.

The application port is exposed:

```dockerfile
EXPOSE 5001
```

A Docker health check is configured using the application's `/health` endpoint.

The container starts using:

```dockerfile
CMD ["python", "run.py"]
```

---

## 3. .dockerignore Explanation

The following files and directories were excluded:

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

Reasons:

* `venv/` contains local Python packages and is unnecessary because dependencies are installed inside the Docker image.
* `__pycache__/` and `*.pyc` are generated Python cache files.
* `.git/` and `.gitignore` are source-control files and are not required at runtime.
* `.pytest_cache/` contains temporary test information.
* `instance/` contains local database storage and should not be packaged into the image because persistent application data is handled using a Docker volume.
* `.env` contains environment-specific configuration and should not be copied into the Docker image.

This reduces the Docker build context and avoids copying unnecessary or sensitive local files.

---

## 4. Image Build Process

The Docker image was successfully built from the Dockerfile.

The first image was built using:

```bash
docker build -t student-api:1.0 .
```

A second version was created:

```bash
docker build -t student-api:1.1 .
```

The images were verified using:

```bash
docker images
```

The resulting versions were:

```text
student-api:1.0
student-api:1.1
```

The Docker image build completed successfully and the resulting image size was approximately 244 MB for the versioned images.

---

## 5. Container Configuration

The application was initially started manually using Docker.

The final container configuration included:

```bash
docker run -d \
  --name student-api-container \
  -p 5001:5001 \
  --env-file .env \
  -v student-api-data:/app/instance \
  student-api:1.0
```

The container runs the Flask application using:

```text
python run.py
```

The container was successfully started and remained in the `Up` state.

---

## 6. Port Mapping

The Flask application listens on container port:

```text
5001
```

The host port is:

```text
5001
```

The mapping is:

```text
5001:5001
```

This means:

```text
Host 127.0.0.1:5001
        |
        v
Docker Container Port 5001
        |
        v
Flask Application
```

The port mapping allows requests sent to the host machine to reach the Flask application inside the container.

A troubleshooting test also demonstrated a different mapping:

```text
5002:5001
```

In that scenario:

* Host Port = 5002
* Container Port = 5001

This demonstrated the difference between host and container ports.

---

## 7. Environment Variables

The application configuration is externalized using environment variables.

The `.env` file contains:

```env
DATABASE_URL=sqlite:///database.db
PORT=5001
DEBUG=False
LOG_LEVEL=INFO
```

The Flask configuration reads these values using `os.getenv()`.

For example:

```python
PORT = int(os.getenv("PORT", "5001"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
```

The container receives the configuration using:

```bash
--env-file .env
```

This allows the same Docker image to be reused with different runtime configuration without rebuilding the image.

The `.env` file itself is excluded from the image using `.dockerignore`.

---

## 8. Volume Configuration

SQLite requires persistent storage so that application data is not lost when a container is removed.

A Docker named volume was created:

```bash
docker volume create student-api-data
```

The volume is mounted into the application instance directory:

```text
student-api-data:/app/instance
```

The volume is also configured in Docker Compose.

The purpose of the volume is to separate persistent database storage from the temporary container filesystem.

Therefore:

```text
Container filesystem
        !=
Persistent Docker volume
```

The container can be removed and recreated while the volume remains available.

---

## 9. Health Check

The Docker image contains a health check using the application's `/health` endpoint.

The check verifies that the Flask application is responding successfully.

The health status was verified with:

```bash
docker inspect --format='{{.State.Health.Status}}' student-api-container
```

The result was:

```text
healthy
```

The API endpoint was also tested externally:

```bash
curl http://127.0.0.1:5001/health
```

Expected result:

```json
{"database":"connected","status":"healthy"}
```

### Running vs Healthy

`Running` means that the container's main process is currently running.

`Healthy` means that the configured Docker health check has successfully verified that the application is responding correctly.

Both are important because a container can be running while the application inside it is not actually functioning correctly.

---

## 10. Logging

Application logs were viewed using Docker:

```bash
docker logs student-api-container
```

Logs can also be followed in real time:

```bash
docker logs -f student-api-container
```

Docker provides application output through the container runtime instead of requiring an operator to inspect internal log files.

This is useful for troubleshooting and operational monitoring.

---

## 11. Docker Compose

A `compose.yaml` file was created to simplify application deployment.

The Compose configuration includes:

* Application service
* Docker image/build configuration
* Port mapping
* Environment variables
* Named volume
* Health check
* Restart policy

The application can be started using:

```bash
docker compose up -d --build
```

The service was verified with:

```bash
docker compose ps
```

The final Compose status showed:

```text
student-api-compose
Up
healthy
0.0.0.0:5001->5001/tcp
```

The health endpoint returned:

```json
{"database":"connected","status":"healthy"}
```

Compose also created the required Docker network and named volume automatically.

---

## 12. Image Versioning

Two application image versions were created:

```text
student-api:1.0
student-api:1.1
```

A small application change was introduced between the versions.

The versions were verified using:

```bash
docker images
```

Image versioning is important because it provides identifiable deployment versions.

It also supports rollback to a previously known version if a newer version introduces a problem.

For example:

```text
Version 1.0 → stable deployment
Version 1.1 → updated deployment
```

---

## 13. Security Considerations

Several basic security improvements were implemented.

### Non-root user

The application runs as:

```text
appuser
```

instead of the root user.

### Slim base image

The image uses:

```text
python:3.12-slim
```

to reduce unnecessary packages and image size.

### Unnecessary files

The `.dockerignore` file prevents local development files and generated files from being included in the build context.

### Sensitive configuration

The `.env` file is not copied into the image.

### Dependency pinning

The project uses pinned dependency versions in `requirements.txt`.

### Remaining limitations

This is a training environment and not a full production security configuration.

Remaining limitations include:

* Automated image vulnerability scanning is not configured.
* Docker secrets management is not implemented.
* SQLite is suitable for this training project but may not be appropriate for a high-scale production deployment.
* Dependency security should be continuously monitored in a production environment.

---

## 14. Known Limitations

The application is designed for a local training environment.

Known limitations include:

* SQLite is not a distributed production database.
* The application uses a fixed internal port of 5001.
* No automated CI/CD image scanning is configured.
* No external production-grade secret manager is configured.
* Docker Compose is intended for local orchestration, while Kubernetes will be used in the next task.

---

## Conclusion

The Student Management API was successfully containerized using Docker.

The completed implementation includes:

```text
Dockerfile                  ✓
.dockerignore               ✓
Docker image                ✓
Versioned images 1.0/1.1    ✓
Docker container             ✓
Environment variables        ✓
Port mapping                 ✓
Docker volume                ✓
Health check                 ✓
Container logs               ✓
Docker Compose               ✓
Basic security improvements  ✓
Troubleshooting tests        ✓
```

The application is successfully running inside Docker and is ready for the next stage: Local Kubernetes Infrastructure.
