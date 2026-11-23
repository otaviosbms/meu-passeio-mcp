from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def budget_only_config(tmp_path: Path) -> Path:
    """Config MCP só com o Budget server (offline, determinístico)."""
    path = tmp_path / "mcp.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "mcpServers": {
                    "budget": {
                        "command": "{python}",
                        "args": ["-m", "meu_passeio.mcp_servers.budget"],
                        "timeout_seconds": 15,
                    },
                    "broken": {
                        "command": "{python}",
                        "args": ["-c", "import sys; sys.exit(1)"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    return path
