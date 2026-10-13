import inspect

from app.admin import repository as admin_repository, service as admin_service
from app.curriculum import repository as curriculum_repository, service as curriculum_service
from app.exercise import repository as exercise_repository, service as exercise_service
from app.progress import repository as progress_repository, service as progress_service
from app.admin import service as admin_service


def test_business_services_delegate_persistence_to_repositories():
    for module in (admin_service,curriculum_service,exercise_service,progress_service):
        source=inspect.getsource(module)
        assert "session.execute(" not in source
        assert "session.add(" not in source
        assert "session.delete(" not in source


def test_repositories_never_commit_transactions():
    for module in (admin_repository,curriculum_repository,exercise_repository,progress_repository):
        assert ".commit(" not in inspect.getsource(module)


def test_admin_use_cases_delegate_domain_rules_to_curriculum_and_exercise():
    assert "curriculum_service.admin_replace_curriculum" in inspect.getsource(admin_service.replace_curriculum)
    assert "curriculum_service.admin_attach_item" in inspect.getsource(admin_service.attach_item)
    assert "curriculum_service.admin_lesson_transition" in inspect.getsource(admin_service.lesson_transition)
    assert "exercise_service.admin_create_assessment" in inspect.getsource(admin_service.create_assessment)
    assert "exercise_service.admin_validate_question" not in inspect.getsource(admin_service)
    assert "exercise_service.admin_create_question" in inspect.getsource(admin_service.create_question)
    source=inspect.getsource(admin_service)
    assert "curriculum_repository" not in source and "exercise_repository" not in source
    assert "begin_nested(" not in source and "INVALID_LIFECYCLE_TRANSITION" not in source
