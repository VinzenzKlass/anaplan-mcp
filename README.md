# anaplan-mcp

MCP server wrapping the [Anaplan SDK](https://github.com/VinzenzKlass/anaplan-sdk).
Plug it into Claude Desktop, Cursor, or any MCP client and talk to Anaplan directly.

## Setup

Add to your MCP client config (`claude_desktop_config.json`, Cursor settings, …):

```json
{
  "mcpServers": {
    "anaplan": {
      "command": "uvx",
      "args": ["anaplan-mcp"],
      "env": {
        "ANAPLAN_WORKSPACE_ID": "...",
        "ANAPLAN_MODEL_ID": "...",
        "ANAPLAN_EMAIL": "me@example.com",
        "ANAPLAN_PASSWORD": "secret"
      }
    }
  }
}
```

Certificate auth is also supported — swap the last two vars for:

```
"ANAPLAN_CERTIFICATE": "/path/to/cert.pem",
"ANAPLAN_PRIVATE_KEY": "/path/to/key.pem"
```

## Python API

For OAuth or any custom auth, use the Python API and pass any `httpx.Auth` subclass:

```python
from anaplan_mcp import AnaplanMCP

# Basic / cert via env vars
AnaplanMCP.from_env().run()

# Explicit credentials
AnaplanMCP(workspace_id="...", user_email="...", password="...").run()
AnaplanMCP(workspace_id="...", certificate="...", private_key="...").run()

# Any httpx.Auth subclass (OAuth, token, …)
from anaplan_sdk._auth import AnaplanLocalOAuth
AnaplanMCP(workspace_id="...", auth=AnaplanLocalOAuth(...)).run()
```

### Filtering tools

```python
AnaplanMCP(..., include={"tr", "audit"})                   # whitelist API groups
AnaplanMCP(..., exclude={"cw"})                            # blacklist API groups
AnaplanMCP(..., exclude_methods={"tr__delete_list_items"}) # suppress specific tools
```

| Group      | Covers                                  |
|------------|-----------------------------------------|
| *(root)*   | Bulk file I/O, imports, exports         |
| `audit`    | Audit log, users                        |
| `tr`       | Lists, modules, transactional writes    |
| `alm`      | Application Lifecycle Management        |
| `cw`       | CloudWorks integrations & connections   |
| `cw.flows` | CloudWorks flows                        |
| `scim`     | User provisioning (SCIM)                |
