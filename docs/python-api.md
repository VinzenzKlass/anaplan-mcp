---
icon: lucide/code
---

# Python API

When the environment-variable approach is too limiting — for example when using OAuth or
any other custom auth flow — you can drive the server directly from Python.

## Starting the server

```python
from anaplan_mcp import AnaplanMCP

# From environment variables (same as the uvx launcher)
AnaplanMCP.from_env().run()

# Explicit basic auth
AnaplanMCP(workspace_id="...", user_email="me@example.com", password="secret").run()

# Certificate auth
AnaplanMCP(workspace_id="...", certificate="/path/to/cert.pem", private_key="/path/to/key.pem").run()

# Any httpx.Auth subclass — OAuth, token exchange, …
from anaplan_sdk._auth import AnaplanLocalOAuth

AnaplanMCP(
    workspace_id="...",
    auth=AnaplanLocalOAuth(client_id="...", client_secret="...", redirect_uri="..."),
).run()
```

## Running locally with non-standard auth

If your auth flow can't be expressed as environment variables, create a small Python
script and point your MCP client at it. The client will launch the script the same way it
would launch `uvx anaplan-mcp`.

**`server.py`**:

```python
from anaplan_sdk._auth import AnaplanLocalOAuth  # or any httpx.Auth subclass
from anaplan_mcp import AnaplanMCP

AnaplanMCP(
    workspace_id="<your-workspace-id>",
    auth=AnaplanLocalOAuth(client_id="...", client_secret="...", redirect_uri="..."),
).run()
```

**MCP client config**:

```json
{
  "mcpServers": {
    "anaplan": {
      "command": "uv",
      "args": ["run", "/path/to/server.py"]
    }
  }
}
```

!!! note
    All credentials stay inside `server.py` — nothing sensitive ends up in the MCP client config.

## Filtering tools

Large tool sets can overwhelm the model context. Use the filtering options to expose only
what you need:

```python
AnaplanMCP(..., include={"tr", "audit"})                    # allowlist API groups
AnaplanMCP(..., exclude={"cw"})                             # denylist API groups
AnaplanMCP(..., exclude_methods={"tr__delete_list_items"})  # suppress specific tools
```

### Available API groups

| Group | Covers |
|---|---|
| *(root)* | Bulk file I/O, imports, exports |
| `audit` | Audit log, users |
| `tr` | Lists, modules, transactional writes |
| `alm` | Application Lifecycle Management |
| `cw` | CloudWorks integrations & connections |
| `cw.flows` | CloudWorks flows |
| `scim` | User provisioning (SCIM) |

