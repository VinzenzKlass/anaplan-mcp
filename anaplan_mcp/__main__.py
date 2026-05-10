"""Entry point for ``anaplan-mcp`` / ``python -m anaplan_mcp``."""

import sys

from anaplan_mcp import AnaplanMCP

_HELP = """\
anaplan-mcp: no credentials found.

Set ONE of the following groups of environment variables, then re-run:

  Certificate auth:
  ANAPLAN_CERTIFICATE           Path to PEM certificate file (or PEM string)
  ANAPLAN_PRIVATE_KEY           Path to PEM private key file (or PEM string)
  ANAPLAN_PRIVATE_KEY_PASSWORD  (optional) Passphrase for encrypted key

  Basic auth:
  ANAPLAN_EMAIL                 Anaplan account email
  ANAPLAN_PASSWORD              Anaplan account password

  Static token:
  ANAPLAN_TOKEN                 Raw Anaplan auth token

Also set (required for most tools):
  ANAPLAN_WORKSPACE_ID          Default workspace ID
  ANAPLAN_MODEL_ID              Default model ID

For Most AI Clients, place these in the "env" block of your MCP JSON config.
See README for full examples.
"""


def main() -> None:
    """Build the server from env vars and start it on stdio."""
    try:
        server = AnaplanMCP.from_env()
    except ValueError:
        print(_HELP, file=sys.stderr)
        sys.exit(1)

    server.run()


if __name__ == "__main__":
    main()
