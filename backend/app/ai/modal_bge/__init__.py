"""Minimal async client boundary for the Modal hosted BGE runtime."""

from app.ai.modal_bge.client import ModalBgeClient, ModalBgeError

__all__ = ["ModalBgeClient", "ModalBgeError"]
