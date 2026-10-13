import ast
import inspect
from pathlib import Path

from app.conversation import repository, service


def test_conversation_repository_never_owns_transactions():
    source_path = Path(inspect.getsourcefile(repository))
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert not (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "session"
                and node.func.attr in {"commit", "rollback"}
            ), f"ConversationRepository directly calls session.{node.func.attr}"


def test_conversation_service_does_not_call_ai_through_repository_or_pass_orm_types():
    source_path = Path(inspect.getsourcefile(service))
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "repository.generate_reply" not in source
    assert "session= session" not in source
    # ChatRequest construction is deliberately scalar-only and contains no
    # AsyncSession/ORM fields; the AI port accepts that value object only.
    chat_request_fields = {"user_id", "conversation_id", "lesson_id", "user_message_id", "content"}
    ai_module = Path(source_path.parent / "ai_chat.py").read_text(encoding="utf-8")
    assert all(f"{field}:" in ai_module for field in chat_request_fields)
    assert "AsyncSession" not in ai_module and "Message" not in ai_module and "Conversation" not in ai_module

