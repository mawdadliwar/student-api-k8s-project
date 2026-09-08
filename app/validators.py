from app.models import Student

ALLOWED_FIELDS = {"name", "age", "email", "phone", "address"}


def validate_student_data(data, is_update=False, student_id=None):
    """
    Validates an incoming student payload.
    Returns a list of error messages (empty list = valid).
    """
    errors = []

    unexpected_fields = set(data.keys()) - ALLOWED_FIELDS
    if unexpected_fields:
        errors.append(f"Unexpected field(s): {', '.join(sorted(unexpected_fields))}")

    name = data.get("name")
    if not name or not str(name).strip():
        errors.append("Name is required")

    age = data.get("age")
    if age is None:
        errors.append("Age is required")
    else:
        try:
            age = int(age)
            if age <= 18:
                errors.append("Age must be greater than 18")
        except (ValueError, TypeError):
            errors.append("Age must be a valid number")

    email = data.get("email")
    if not email or not str(email).strip():
        errors.append("Email must not be empty")
    else:
        query = Student.query.filter_by(email=email)
        if is_update and student_id is not None:
            query = query.filter(Student.id != student_id)
        if query.first():
            errors.append("Email already exists")

    return errors