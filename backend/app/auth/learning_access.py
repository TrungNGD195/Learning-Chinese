"""Server-configured test learners bypass prerequisites, never authorization.

Immutable account IDs only: names, email prefixes and request payloads must not
grant this capability. No completion timestamps or grades are fabricated.
"""
from app.auth import repository
from app.core.config import get_settings


async def bypasses_learning_prerequisites(session, user_id) -> bool:
    if user_id not in get_settings().learning_test_user_ids:
        return False
    user = await repository.get_user_by_id(session, user_id)
    return bool(user and user.is_active and user.role == "LEARNER")
