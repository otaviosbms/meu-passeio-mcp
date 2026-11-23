"""Integração real via stdio: MCP Client Manager <-> Budget MCP Server (sem rede)."""

from pathlib import Path

from meu_passeio.modules.mcp.client_manager import McpClientManager
from meu_passeio.modules.mcp.config import load_mcp_config

ROOT = Path(__file__).resolve().parents[1]


async def test_discovers_tools_and_calls_budget(budget_only_config: Path):
    manager = McpClientManager(load_mcp_config(budget_only_config), cwd=ROOT, connect_timeout=20)
    await manager.start()
    try:
        status = {s["name"]: s["status"] for s in manager.status()}
        assert status == {"budget": "connected", "broken": "failed"}  # falha isolada, app segue

        names = {t.qualified_name for t in manager.catalog.all()}
        assert names == {
            "budget__calculate_fuel_cost",
            "budget__estimate_trip_cost",
            "budget__calculate_budget_breakdown",
        }

        ok = await manager.call_tool(
            "budget", "calculate_fuel_cost", {"distance_km": 100, "fuel_price_per_liter": 6}
        )
        assert ok.ok, ok.error
        assert ok.data["estimated_cost"] == 100.0  # 200 km / 12 km/l * 6

        invalid = await manager.call_tool("budget", "calculate_fuel_cost", {"distance_km": "x"})
        assert not invalid.ok and "inválidos" in (invalid.error or "")

        unknown = await manager.call_tool("budget", "drop_tables", {})
        assert not unknown.ok and "não permitida" in (unknown.error or "")

        unavailable = await manager.call_tool("broken", "anything", {})
        assert not unavailable.ok
    finally:
        await manager.stop()
