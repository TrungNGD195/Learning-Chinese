from __future__ import annotations

from typing import Any, Callable

from app.core.config import Settings, get_settings


class ModalBgeError(Exception):
    """Safe, provider-neutral indication that Modal could not serve an operation."""

    def __init__(self, code: str = "MODAL_PROVIDER_FAILED") -> None:
        super().__init__(code)
        self.code = code


class ModalBgeClient:
    """Resolve a configured Modal class and invoke only its native async method."""

    def __init__(self, settings: Settings | None = None, *, class_lookup: Callable | None = None):
        self.settings = settings or get_settings()
        self._class_lookup = class_lookup

    @property
    def real_modal_runtime(self) -> bool:
        """True only when lookup will use the Modal SDK, not an injected test lookup."""
        return self._class_lookup is None

    def _lookup(self):
        if not all((self.settings.modal_bge_app_name, self.settings.modal_bge_class_name,
                    self.settings.modal_environment)):
            raise ModalBgeError("MODAL_PROVIDER_NOT_CONFIGURED")
        try:
            if self._class_lookup is not None:
                return self._class_lookup(
                    self.settings.modal_bge_app_name,
                    self.settings.modal_bge_class_name,
                    self.settings.modal_environment,
                )
            import modal

            sdk_client = modal.Client.from_credentials(
                self.settings.modal_token_id.get_secret_value(),
                self.settings.modal_token_secret.get_secret_value(),
            )

            return modal.Cls.from_name(
                self.settings.modal_bge_app_name,
                self.settings.modal_bge_class_name,
                environment_name=self.settings.modal_environment,
                client=sdk_client,
            )
        except Exception:
            # Never include SDK exceptions: they may contain workspace or request data.
            raise ModalBgeError("MODAL_LOOKUP_FAILED") from None

    async def invoke(self, method_name: str, *args, **kwargs) -> Any:
        try:
            cls = self._lookup()
            instance = cls()
            method = getattr(instance, method_name)
            return await method.remote.aio(*args, **kwargs)
        except ModalBgeError:
            raise
        except Exception as exc:
            kind = type(exc).__name__.lower()
            code = "MODAL_LOOKUP_FAILED" if any(
                marker in kind for marker in ("auth", "permission", "notfound", "not_found", "lookup", "resource")
            ) else "MODAL_INVOCATION_FAILED"
            raise ModalBgeError(code) from None
