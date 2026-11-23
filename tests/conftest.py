from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import yaml
from google_fakes import FAKE_KEY, FakeGoogle

from meu_passeio.mcp_server.common import google as gcommon

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


@pytest.fixture
def fake_google(monkeypatch: pytest.MonkeyPatch) -> FakeGoogle:
    """Substitui o cliente do Google Maps por um simulador sem rede."""
    fake = FakeGoogle()
    client = gcommon.GoogleMapsClient(
        FAKE_KEY,
        httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)),
        language="pt-BR",
        region="BR",
    )
    monkeypatch.setattr(gcommon, "_client", client)
    return fake
