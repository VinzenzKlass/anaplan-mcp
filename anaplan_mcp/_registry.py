from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any

import anaplan_sdk
from anaplan_sdk._async_clients import (  # pyright: ignore[reportPrivateUsage]
    AsyncClient,
    _AsyncAlmClient,  # pyright: ignore[reportPrivateUsage]
    _AsyncAuditClient,  # pyright: ignore[reportPrivateUsage]
    _AsyncCloudWorksClient,  # pyright: ignore[reportPrivateUsage]
    _AsyncScimClient,  # pyright: ignore[reportPrivateUsage]
    _AsyncTransactionalClient,  # pyright: ignore[reportPrivateUsage]
)
from anaplan_sdk._async_clients._cw_flow import (  # pyright: ignore[reportPrivateUsage]
    _AsyncFlowClient,  # pyright: ignore[reportPrivateUsage]
)
from fastmcp import FastMCP

from ._filters import clean_parameters, should_skip

logger = logging.getLogger(__name__)

# Maps dot-separated attribute path → (tool_prefix, SDK class, tags)
_NAMESPACES: dict[str, tuple[str, type, frozenset[str]]] = {
    "": ("", AsyncClient, frozenset({"bulk"})),
    "audit": ("audit", _AsyncAuditClient, frozenset({"audit"})),
    "tr": ("tr", _AsyncTransactionalClient, frozenset({"transactional"})),
    "alm": ("alm", _AsyncAlmClient, frozenset({"alm"})),
    "cw": ("cw", _AsyncCloudWorksClient, frozenset({"cloud_works"})),
    "cw.flows": ("cw__flows", _AsyncFlowClient, frozenset({"cloud_works", "flows"})),
    "scim": ("scim", _AsyncScimClient, frozenset({"scim"})),
}


def _resolve_nested(client: anaplan_sdk.AsyncClient, path: str) -> Any:
    obj: Any = client
    for part in path.split("."):
        if part:
            obj = getattr(obj, part)
    return obj


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list):
        return [_serialize(item) for item in value]  # type: ignore[misc]
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}  # type: ignore[misc]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _make_wrapper(
    ns_path: str,
    attr_name: str,
    tool_name: str,
    params: list[inspect.Parameter],
    docstring: str,
    client: anaplan_sdk.AsyncClient,
) -> Any:
    """Return an async function that delegates to *client* with the correct signature."""

    async def _tool(**kwargs: Any) -> Any:
        obj = _resolve_nested(client, ns_path)
        result = await getattr(obj, attr_name)(**kwargs)
        return _serialize(result)

    _tool.__name__ = tool_name
    _tool.__qualname__ = tool_name
    _tool.__doc__ = docstring
    _tool.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
    _tool.__annotations__ = {
        p.name: p.annotation for p in params if p.annotation is not inspect.Parameter.empty
    }
    return _tool


def _register_namespace(
    mcp: FastMCP,
    ns_path: str,
    cls: type,
    prefix: str,
    tags: frozenset[str],
    exclude_methods: frozenset[str],
    client: anaplan_sdk.AsyncClient,
) -> int:
    registered = 0
    for attr_name in sorted(dir(cls)):
        if attr_name.startswith("_"):
            continue
        class_method = getattr(cls, attr_name, None)
        if class_method is None:
            continue

        tool_name = f"{prefix}__{attr_name}" if prefix else attr_name

        if attr_name in exclude_methods or tool_name in exclude_methods:
            logger.debug("Skipping excluded method '%s'.", tool_name)
            continue
        if should_skip(attr_name, class_method):
            logger.debug("Skipping '%s' (filtered).", tool_name)
            continue

        params = clean_parameters(class_method)
        docstring = inspect.getdoc(class_method) or tool_name
        wrapper = _make_wrapper(ns_path, attr_name, tool_name, params, docstring, client)
        mcp.tool(name=tool_name, description=docstring, tags=set(tags))(wrapper)
        registered += 1

    return registered


def _register_file_tools(
    mcp: FastMCP,
    include: frozenset[str] | None,
    exclude: frozenset[str],
    exclude_methods: frozenset[str],
    client: anaplan_sdk.AsyncClient,
) -> int:
    """Register path-based wrappers for binary I/O methods excluded from auto-discovery."""

    entries: list[tuple[str, str, frozenset[str], Any]] = []

    async def get_file(*, file_id: int, path: str) -> str:
        """Download a file from Anaplan and write its content to *path*. Returns *path*."""
        Path(path).write_bytes(await client.get_file(file_id))
        return path

    async def upload_file(*, file_id: int, path: str) -> None:
        """Read the local file at *path* and upload it to Anaplan."""
        await client.upload_file(file_id, Path(path).read_bytes())

    async def export_and_download(*, action_id: int, path: str) -> str:
        """Run an export action and write the resulting file to *path*. Returns *path*."""
        Path(path).write_bytes(await client.export_and_download(action_id))
        return path

    async def upload_and_import(
        *, file_id: int, path: str, action_id: int, wait_for_completion: bool = True
    ) -> Any:
        """Read the local file at *path*, upload it, then run the given import action."""
        task = await client.upload_and_import(  # type: ignore[call-overload]
            file_id, Path(path).read_bytes(), action_id, wait_for_completion
        )
        return _serialize(task)

    async def get_optimizer_log(*, action_id: int, task_id: str, path: str) -> str:
        """Download the optimizer solution log for a task and write it to *path*."""
        Path(path).write_bytes(await client.get_optimizer_log(action_id, task_id))
        return path

    for fn in (get_file, upload_file, export_and_download, upload_and_import, get_optimizer_log):
        entries.append(("", fn.__name__, frozenset({"bulk"}), fn))

    async def cw_get_import_error_dump(*, run_id: str, path: str) -> str:
        """Download the error dump for a CloudWorks import run and write it to *path*."""
        Path(path).write_bytes(await client.cw.get_import_error_dump(run_id))
        return path

    async def cw_get_process_error_dump(*, run_id: str, action_id: int | str, path: str) -> str:
        """Download the error dump for an action within a CloudWorks process run to *path*."""
        Path(path).write_bytes(await client.cw.get_process_error_dump(run_id, action_id))
        return path

    for fn in (cw_get_import_error_dump, cw_get_process_error_dump):
        entries.append(("cw", fn.__name__, frozenset({"cloud_works"}), fn))

    async def alm__get_comparison_report(
        *, source_revision_id: str, source_model_id: str, target_revision_id: str, path: str
    ) -> str:
        """
        Generate a full comparison report between two revisions and write it to *path*.

        Combines report creation and download into one call. Returns *path*.
        """
        task = await client.alm.create_comparison_report(
            source_revision_id, source_model_id, target_revision_id
        )
        Path(path).write_bytes(await client.alm.get_comparison_report(task))
        return path

    entries.append(
        ("alm", "alm__get_comparison_report", frozenset({"alm"}), alm__get_comparison_report)
    )

    registered = 0
    for ns_key, tool_name, tags, fn in entries:
        if include is not None and ns_key not in include:
            continue
        if ns_key in exclude:
            continue
        if tool_name in exclude_methods or tool_name.split("__")[-1] in exclude_methods:
            continue
        mcp.tool(name=tool_name, description=inspect.getdoc(fn) or tool_name, tags=set(tags))(fn)
        registered += 1

    return registered


def register_all_tools(
    mcp: FastMCP,
    client: anaplan_sdk.AsyncClient,
    *,
    include: frozenset[str] | None,
    exclude: frozenset[str],
    exclude_methods: frozenset[str],
) -> None:
    total = 0
    for ns_path, (prefix, cls, tags) in _NAMESPACES.items():
        if include is not None and ns_path not in include:
            continue
        if ns_path in exclude:
            continue
        n = _register_namespace(mcp, ns_path, cls, prefix, tags, exclude_methods, client)
        total += n
        if n:
            label = f"'{ns_path}'" if ns_path else "top-level"
            logger.info("Registered %d tool(s) from %s.", n, label)

    logger.info("Total MCP tools registered: %d.", total)

    n = _register_file_tools(
        mcp, include=include, exclude=exclude, exclude_methods=exclude_methods, client=client
    )
    if n:
        logger.info("Registered %d file I/O tool(s).", n)
