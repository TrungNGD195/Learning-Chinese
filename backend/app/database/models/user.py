from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Uuid, func

from app.database.models._factory import model

User = model(
    "User", "users",
    [("id", Uuid(as_uuid=True), {"primary_key": True, "default": uuid4}),
     ("email", String, {"nullable": False, "unique": True}),
     ("password_hash", String, {"nullable": False}),
     ("full_name", String, {"nullable": False}),
     ("role", String, {"nullable": False}),
     ("is_active", Boolean, {"nullable": False, "server_default": "true"}),
     ("created_at", DateTime(timezone=True), {"nullable": False, "server_default": func.now()}),
     ("updated_at", DateTime(timezone=True), {"nullable": False, "server_default": func.now(), "onupdate": func.now()})],
    CheckConstraint("role IN ('LEARNER', 'ADMIN')", name="role_values"),
)
