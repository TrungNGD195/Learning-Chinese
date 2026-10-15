import asyncio
from types import SimpleNamespace

import pytest

from app.ai.modal_bge.client import ModalBgeClient, ModalBgeError
from app.core.config import Settings


def settings(**values):
    base = dict(
        _env_file=None, app_env="test", debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="test-only-secret", embedding_provider="modal",
        modal_token_id="not-a-real-token-id", modal_token_secret="not-a-real-token-secret",
        modal_environment="test-env", modal_bge_app_name="bge-app", modal_bge_class_name="BgeInference",
    )
    base.update(values)
    return Settings(**base)


class RemoteMethod:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []
        self.remote = self
        self.aio = self.async_call

    def __call__(self, *_args, **_kwargs):
        raise AssertionError("blocking Modal .remote() must never be called")

    async def async_call(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error
        return self.result


def test_lookup_configuration_and_native_async_remote_only():
    method = RemoteMethod({"ok": True})
    seen = []

    class RemoteClass:
        def __call__(self):
            return SimpleNamespace(embed_query=method)

    client = ModalBgeClient(settings(), class_lookup=lambda *args: (seen.append(args) or RemoteClass()))
    assert client.real_modal_runtime is False
    assert ModalBgeClient(settings()).real_modal_runtime is True
    assert asyncio.run(client.invoke("embed_query", "q")) == {"ok": True}
    assert seen == [("bge-app", "BgeInference", "test-env")]
    assert method.calls == [(('q',), {})]


@pytest.mark.parametrize("name", ["AuthError", "NotFoundError", "PermissionDeniedError"])
def test_modal_lookup_and_sdk_errors_are_normalized_without_details(name):
    Error = type(name, (RuntimeError,), {})
    client = ModalBgeClient(settings(), class_lookup=lambda *_: (_ for _ in ()).throw(Error("secret request text")))
    with pytest.raises(ModalBgeError) as caught:
        asyncio.run(client.invoke("embed_query", "private learner text"))
    assert caught.value.code == "MODAL_LOOKUP_FAILED"
    assert "secret" not in str(caught.value)
    assert "private learner text" not in str(caught.value)


def test_invocation_failure_is_safe_and_never_retries():
    method = RemoteMethod(error=RuntimeError("token and private payload"))

    class RemoteClass:
        def __call__(self): return SimpleNamespace(embed_query=method)

    client = ModalBgeClient(settings(), class_lookup=lambda *_: RemoteClass())
    with pytest.raises(ModalBgeError) as caught:
        asyncio.run(client.invoke("embed_query", "private text"))
    assert caught.value.code == "MODAL_INVOCATION_FAILED"
    assert method.calls == [(('private text',), {})]
    assert "token" not in str(caught.value) and "private text" not in str(caught.value)
