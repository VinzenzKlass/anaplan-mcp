from __future__ import annotations

import collections.abc
import inspect
import types
import typing
from contextlib import suppress
from typing import Any

from pydantic import TypeAdapter

_BINARY_TYPES: frozenset[type] = frozenset({bytes, bytearray})

_STREAMING_ORIGINS: frozenset[Any] = frozenset(
    {
        collections.abc.AsyncIterator,
        collections.abc.AsyncGenerator,
        collections.abc.Iterator,
        collections.abc.Generator,
    }
)

_ALWAYS_SKIP: frozenset[str] = frozenset({"with_model"})
_STRIP_PARAMS: frozenset[str] = frozenset({"self"})


def _flatten_union(annotation: Any) -> tuple[Any, ...]:
    """Return the constituent types of a ``Union`` / ``X | Y`` annotation."""
    origin = getattr(annotation, "__origin__", None)
    if origin is typing.Union or origin is types.UnionType:
        return annotation.__args__
    return (annotation,)


def is_binary_or_streaming(annotation: Any) -> bool:
    """Return *True* if the annotation includes binary or streaming types."""
    if annotation is inspect.Parameter.empty or annotation is None:
        return False
    for t in _flatten_union(annotation):
        if t in _BINARY_TYPES:
            return True
        origin = getattr(t, "__origin__", None)
        if origin in _STREAMING_ORIGINS:
            return True
    return False


def should_skip(name: str, method: Any) -> bool:
    """
    Return *True* if *method* should not be exposed as an MCP tool.

    Skipped when the method is private, not an async coroutine, or involves
    binary / streaming I/O in its parameters or return type.
    """
    if name.startswith("_"):
        return True
    if name in _ALWAYS_SKIP:
        return True
    if not callable(method):
        return True
    if not inspect.iscoroutinefunction(method):
        return True

    try:
        sig = inspect.signature(method)
        hints = typing.get_type_hints(method)
    except (TypeError, ValueError):
        return True

    for param_name, param in sig.parameters.items():
        if param_name in _STRIP_PARAMS:
            continue
        annotation = hints.get(param_name, param.annotation)
        if is_binary_or_streaming(annotation):
            return True

    return is_binary_or_streaming(hints.get("return"))


def _is_pydantic_compatible(annotation: Any) -> bool:
    with suppress(Exception):
        TypeAdapter(annotation)
        return True
    return False


def clean_parameters(method: Any) -> list[inspect.Parameter]:
    """
    Return the parameters of *method* ready for tool registration.

    Strips ``self`` and resolves all forward-reference type hints.
    Any annotation that Pydantic cannot handle is replaced with ``Any``.
    """
    try:
        sig = inspect.signature(method)
        hints = typing.get_type_hints(method)
    except (TypeError, ValueError):
        return []

    result: list[inspect.Parameter] = []
    for pname, param in sig.parameters.items():
        if pname in _STRIP_PARAMS:
            continue
        annotation = hints.get(pname, param.annotation)
        if not _is_pydantic_compatible(annotation):
            annotation = Any
        result.append(param.replace(annotation=annotation))
    return result
