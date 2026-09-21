from flask_sqlalchemy import SQLAlchemy
from prometheus_client import Counter, Histogram

db = SQLAlchemy()

REQUEST_COUNT = Counter('student_api_requests_total', 'Total API Requests', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('student_api_request_duration_seconds', 'Request duration in seconds', ['endpoint'])
REQUEST_ERRORS = Counter('student_api_request_errors_total', 'Total API Errors', ['endpoint', 'http_status'])