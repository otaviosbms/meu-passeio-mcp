from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVER = "meu-passeio"


@pytest.fixture
def mcp_test_config(tmp_path: Path) -> Path:
    """Config MCP com o server Meu Passeio e um server quebrado (para testar isolamento).

    Os testes só chamam as tools de orçamento, que são offline e determinísticas.
    """
    path = tmp_path / "mcp.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "mcpServers": {
                    SERVER: {
                        "command": "{python}",
                        "args": ["-m", "meu_passeio.mcp_server"],
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
