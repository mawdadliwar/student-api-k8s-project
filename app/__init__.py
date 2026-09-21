import logging
import time

from flask import Flask, request
from dotenv import load_dotenv
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import Config
from app.extensions import db, REQUEST_COUNT, REQUEST_LATENCY, REQUEST_ERRORS

load_dotenv()


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config["APP_VERSION"] = "2.0.0"

    logging.basicConfig(
        level=getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    db.init_app(app)

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    from app.routes import bp as api_bp
    app.register_blueprint(api_bp)

    @app.route("/metrics", methods=["GET"])
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    @app.before_request
    def start_timer():
        request.start_time = time.time()

    @app.after_request
    def record_metrics(response):
        if hasattr(request, 'start_time'):
            resp_time = time.time() - request.start_time
            endpoint = request.endpoint or 'unknown'
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(resp_time)
            REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, http_status=response.status_code).inc()
            if response.status_code >= 400:
                REQUEST_ERRORS.labels(endpoint=endpoint, http_status=response.status_code).inc()
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        return {"error": "Not Found", "status": 404, "path": request.path}, 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return {"error": "Method Not Allowed", "status": 405, "path": request.path}, 405

    @app.errorhandler(500)
    def handle_internal_error(error):
        db.session.rollback()
        logger.exception("Unhandled exception")
        return {"error": "Internal Server Error", "status": 500, "path": request.path}, 500

    logger.info(
        "Student Management API starting up (debug=%s, database=%s)",
        app.config.get("DEBUG"),
        app.config.get("SQLALCHEMY_DATABASE_URI"),
    )

    return app