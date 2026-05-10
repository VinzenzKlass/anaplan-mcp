from __future__ import annotations

import logging
import os
from typing import Any

import anaplan_sdk
import httpx
from fastmcp import FastMCP
from fastmcp.server.server import Transport

from ._registry import register_all_tools

logger = logging.getLogger(__name__)


class AnaplanMCP:
    """
    Local MCP server that exposes the full Anaplan API as AI tools.

    One server = one :class:`anaplan_sdk.AsyncClient`.

    **Certificate auth**::

        server = AnaplanMCP(
            workspace_id="8a8b8c8d8e8f",
            certificate="/path/to/cert.pem",
            private_key="/path/to/key.pem",
        )
        server.run()

    **Basic auth**::

        server = AnaplanMCP(
            workspace_id="8a8b8c8d8e8f",
            user_email="me@example.com",
            password="secret",
        )
        server.run()

    **Custom / OAuth auth — bring your own** ``httpx.Auth``::

        from anaplan_sdk._auth import AnaplanLocalOAuth

        server = AnaplanMCP(
            workspace_id="8a8b8c8d8e8f",
            auth=AnaplanLocalOAuth(client_id="...", client_secret="...", redirect_uri="..."),
        )
        server.run()

    **From environment variables**::

        server = AnaplanMCP.from_env()
        server.run()
    """

    def __init__(
        self,
        workspace_id: str | None = None,
        model_id: str | None = None,
        *,
        auth: httpx.Auth | None = None,
        certificate: str | bytes | None = None,
        private_key: str | bytes | None = None,
        private_key_password: str | bytes | None = None,
        user_email: str | None = None,
        password: str | None = None,
        name: str = "Anaplan MCP",
        include: set[str] | None = None,
        exclude: set[str] | None = None,
        exclude_methods: set[str] | None = None,
        **fastmcp_kwargs: Any,
    ) -> None:
        ws = workspace_id or os.environ.get("ANAPLAN_WORKSPACE_ID")
        mid = model_id or os.environ.get("ANAPLAN_MODEL_ID")

        if auth is not None:
            logger.info("%s configured.", type(auth).__name__)
        elif certificate and private_key:
            from anaplan_sdk._auth import _AnaplanCertAuth  # pyright: ignore[reportPrivateUsage]

            auth = _AnaplanCertAuth(certificate, private_key, private_key_password)
            logger.info("Certificate auth configured.")
        elif user_email and password:
            from anaplan_sdk._auth import _AnaplanBasicAuth  # pyright: ignore[reportPrivateUsage]

            auth = _AnaplanBasicAuth(user_email, password)
            logger.info("Basic auth configured.")
        else:
            raise ValueError(
                "Credentials required. Provide one of:\n"
                "  auth=<httpx.Auth>          (any httpx.Auth subclass — OAuth, custom, …)\n"
                "  certificate + private_key  (certificate auth)\n"
                "  user_email + password      (basic auth)"
            )

        client = anaplan_sdk.AsyncClient(workspace_id=ws, model_id=mid, auth=auth)
        self._mcp: FastMCP = FastMCP(name, **fastmcp_kwargs)
        register_all_tools(
            self._mcp,
            client,
            include=frozenset(include) if include is not None else None,
            exclude=frozenset(exclude or ()),
            exclude_methods=frozenset(exclude_methods or ()),
        )

    @classmethod
    def from_env(cls, **kwargs: Any) -> "AnaplanMCP":
        """
        Build an :class:`AnaplanMCP` server from environment variables.

        Credential resolution (first match wins):

        * **Certificate auth** — ``ANAPLAN_CERTIFICATE`` + ``ANAPLAN_PRIVATE_KEY``
          (+ optional ``ANAPLAN_PRIVATE_KEY_PASSWORD``)
        * **Basic auth** — ``ANAPLAN_EMAIL`` + ``ANAPLAN_PASSWORD``

        For any other auth strategy (OAuth, token, …) construct the
        :class:`httpx.Auth` yourself and pass it via ``auth=`` directly.
        """
        return cls(
            workspace_id=os.environ.get("ANAPLAN_WORKSPACE_ID"),
            model_id=os.environ.get("ANAPLAN_MODEL_ID"),
            certificate=os.environ.get("ANAPLAN_CERTIFICATE"),
            private_key=os.environ.get("ANAPLAN_PRIVATE_KEY"),
            private_key_password=os.environ.get("ANAPLAN_PRIVATE_KEY_PASSWORD"),
            user_email=os.environ.get("ANAPLAN_EMAIL"),
            password=os.environ.get("ANAPLAN_PASSWORD"),
            **kwargs,
        )

    @property
    def mcp(self) -> FastMCP:
        """The underlying :class:`~fastmcp.FastMCP` instance."""
        return self._mcp

    def run(
        self,
        transport: Transport | None = None,
        show_banner: bool | None = None,
        **transport_kwargs: Any,
    ) -> None:
        """Start the MCP server (blocking). Defaults to stdio."""
        self._mcp.run(transport, show_banner, **transport_kwargs)

    async def run_async(
        self,
        transport: Transport | None = None,
        show_banner: bool | None = None,
        **transport_kwargs: Any,
    ) -> None:
        """Start the MCP server from within a running event loop."""
        await self._mcp.run_async(transport, show_banner, **transport_kwargs)

    def __repr__(self) -> str:
        return f"AnaplanMCP(name={self._mcp.name!r})"
