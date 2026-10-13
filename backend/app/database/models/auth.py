from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, Uuid, func

from app.database.models._factory import model

RefreshToken = model(
    "RefreshToken", "refresh_tokens",
    [("id", Uuid(as_uuid=True), {"primary_key": True, "default": uuid4}),
     ("user_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "users.id", "ondelete": "CASCADE"}),
     ("token_hash", Text, {"nullable": False, "unique": True}),
     ("expires_at", DateTime(timezone=True), {"nullable": False}),
     ("revoked_at", DateTime(timezone=True)),
     ("created_at", DateTime(timezone=True), {"nullable": False, "server_default": func.now()})],
    indexes=(Index("ix_refresh_tokens_user_id", "user_id"), Index("ix_refresh_tokens_expires_at", "expires_at")),
)

PasswordResetToken = model(
    "PasswordResetToken", "password_reset_tokens",
    [("id", Uuid(as_uuid=True), {"primary_key": True, "default": uuid4}),
     ("user_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "users.id", "ondelete": "CASCADE"}),
     ("token_hash", Text, {"nullable": False, "unique": True}),
     ("expires_at", DateTime(timezone=True), {"nullable": False}),
     ("used_at", DateTime(timezone=True)),
     ("created_at", DateTime(timezone=True), {"nullable": False, "server_default": func.now()})],
    indexes=(Index("ix_password_reset_tokens_user_id", "user_id"), Index("ix_password_reset_tokens_expires_at", "expires_at")),
)
