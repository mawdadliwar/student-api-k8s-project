import logging

from flask import Blueprint, request, jsonify
from sqlalchemy import text

from app.extensions import db
from app.models import Student
from app.validators import validate_student_data

logger = logging.getLogger(__name__)

bp = Blueprint("api", __name__)


@bp.before_request
def log_incoming_request():
    logger.info(f"Incoming request: {request.method} {request.path}")


@bp.after_request
def log_outgoing_response(response):
    logger.info(f"Completed request: {request.method} {request.path} -> {response.status_code}")
    return response


@bp.route("/")
def home():
    return {"message": "Student API Running"}, 200


@bp.route("/health", methods=["GET"])
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}, 200
    except Exception:
        logger.exception("Health check failed: database unreachable")
        return {"status": "unhealthy", "database": "unavailable"}, 503


@bp.route("/students", methods=["GET"])
def get_students():
    name_filter = request.args.get("name")
    page = request.args.get("page", type=int)
    size = request.args.get("size", type=int)

    query = Student.query
    if name_filter:
        query = query.filter(Student.name.ilike(f"%{name_filter}%"))

    if page is not None or size is not None:
        page = page if page and page > 0 else 1
        size = size if size and size > 0 else 10
        pagination = query.paginate(page=page, per_page=size, error_out=False)
        return jsonify({
            "page": pagination.page,
            "size": size,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
            "students": [s.to_dict() for s in pagination.items]
        }), 200

    students = query.all()
    return jsonify([s.to_dict() for s in students]), 200


@bp.route("/students/<int:id>", methods=["GET"])
def get_student(id):
    student = Student.query.get(id)
    if not student:
        logger.warning(f"Requested student {id} not found")
        return {"message": "Student not found"}, 404
    return jsonify(student.to_dict()), 200


@bp.route("/students", methods=["POST"])
def create_student():
    data = request.get_json(silent=True)
    if not data:
        return {"message": "Request body must be JSON"}, 400

    errors = validate_student_data(data)
    if errors:
        logger.warning(f"Student creation validation failed: {errors}")
        return {"message": "Validation failed", "errors": errors}, 400

    student = Student(
        name=data["name"],
        age=data["age"],
        email=data["email"],
        phone=data.get("phone"),
        address=data.get("address"),
    )

    try:
        db.session.add(student)
        db.session.commit()
        logger.info(f"Student created successfully: id={student.id}")
        return jsonify(student.to_dict()), 201
    except Exception:
        db.session.rollback()
        logger.exception("Database error while creating student")
        return {"message": "Database error occurred while creating the student"}, 500


@bp.route("/students/<int:id>", methods=["PUT"])
def update_student(id):
    student = Student.query.get(id)
    if not student:
        logger.warning(f"Update failed: student {id} not found")
        return {"message": "Student not found"}, 404

    data = request.get_json(silent=True)
    if not data:
        return {"message": "Request body must be JSON"}, 400

    errors = validate_student_data(data, is_update=True, student_id=id)
    if errors:
        logger.warning(f"Student update validation failed for id={id}: {errors}")
        return {"message": "Validation failed", "errors": errors}, 400

    student.name = data["name"]
    student.age = data["age"]
    student.email = data["email"]
    student.phone = data.get("phone")
    student.address = data.get("address")

    try:
        db.session.commit()
        logger.info(f"Student {id} updated successfully")
        return jsonify(student.to_dict()), 200
    except Exception:
        db.session.rollback()
        logger.exception(f"Database error while updating student {id}")
        return {"message": "Database error occurred while updating the student"}, 500


@bp.route("/students/<int:id>", methods=["DELETE"])
def delete_student(id):
    student = Student.query.get(id)
    if not student:
        logger.warning(f"Delete failed: student {id} not found")
        return {"message": "Student not found"}, 404

    try:
        db.session.delete(student)
        db.session.commit()
        logger.info(f"Student {id} deleted successfully")
        return {"message": "Student deleted"}, 200
    except Exception:
        db.session.rollback()
        logger.exception(f"Database error while deleting student {id}")
        return {"message": "Database error occurred while deleting the student"}, 500