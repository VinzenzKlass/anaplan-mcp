---
icon: lucide/rocket
---

# Get started

**anaplan-mcp** is an [MCP](https://modelcontextprotocol.io/) server that wraps the
[Anaplan SDK](https://github.com/VinzenzKlass/anaplan-sdk) and exposes the full Anaplan
API as AI tools — plug it into Claude Desktop, Cursor, or any MCP-compatible client and
talk to Anaplan directly.

## Installation

No installation step is needed for the standard setup. The `uvx` launcher fetches
and runs the package on demand.

For the Python API (custom auth, filtering, …) install the package into your project:

```bash
uv add anaplan-mcp
# or
pip install anaplan-mcp
```

## Quick setup

Add the following to your MCP client config (`claude_desktop_config.json`, Cursor settings, …):

=== "Basic auth"

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

=== "Certificate auth"

    ```json
    {
      "mcpServers": {
        "anaplan": {
          "command": "uvx",
          "args": ["anaplan-mcp"],
          "env": {
            "ANAPLAN_WORKSPACE_ID": "...",
            "ANAPLAN_MODEL_ID": "...",
            "ANAPLAN_CERTIFICATE": "/path/to/cert.pem",
            "ANAPLAN_PRIVATE_KEY": "/path/to/key.pem"
          }
        }
      }
    }
    ```

!!! tip "ANAPLAN_MODEL_ID is optional"
    Setting a default model ID avoids having to specify it on every tool call.
    You can still override it per-call at runtime.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANAPLAN_WORKSPACE_ID` | Recommended | Default workspace for all tool calls |
| `ANAPLAN_MODEL_ID` | Optional | Default model for all tool calls |
| `ANAPLAN_EMAIL` | Basic auth | Anaplan account e-mail |
| `ANAPLAN_PASSWORD` | Basic auth | Anaplan account password |
| `ANAPLAN_CERTIFICATE` | Cert auth | Path to PEM certificate (or PEM string) |
| `ANAPLAN_PRIVATE_KEY` | Cert auth | Path to PEM private key (or PEM string) |
| `ANAPLAN_PRIVATE_KEY_PASSWORD` | Cert auth | Passphrase for an encrypted key (optional) |
