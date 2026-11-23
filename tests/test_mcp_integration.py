"""Integração real via stdio: MCP Client Manager <-> MCP Server do Meu Passeio."""

from pathlib import Path

from conftest import SERVER

from meu_passeio.modules.mcp.client_manager import McpClientManager
from meu_passeio.modules.mcp.config import load_mcp_config

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TOOLS = {
    "search_places",
    "search_restaurants",
    "get_place_details",
    "check_opening_hours",
    "find_nearby",
    "search_along_route",
    "calculate_distance",
    "get_route",
    "estimate_toll_costs",
    "get_travel_time",
    "optimize_stops",
    "get_forecast",
    "get_weather_by_date",
    "get_climate_normals",
    "get_sun_times",
    "convert_currency",
    "get_fuel_price",
    "calculate_fuel_cost",
    "estimate_meal_cost",
    "estimate_trip_cost",
    "calculate_budget_breakdown",
    "suggest_day_trip_destinations",
    "optimize_day_itinerary",
    "get_holidays",
    "save_trip",
    "list_trips",
    "get_trip",
    "update_trip",
}


async def test_single_server_exposes_all_tools(mcp_test_config: Path):
    manager = McpClientManager(load_mcp_config(mcp_test_config), cwd=ROOT, connect_timeout=20)
    await manager.start()
    try:
        status = {s["name"]: s["status"] for s in manager.status()}
        assert status == {SERVER: "connected", "broken": "failed"}  # falha isolada, app segue

        tools = {t.tool for t in manager.catalog.all() if t.server == SERVER}
        assert tools == EXPECTED_TOOLS

        ok = await manager.call_tool(
            SERVER,
            "calculate_fuel_cost",
            {"distance_km": 100, "fuel_price_per_liter": 6},
        )
        assert ok.ok, ok.error
        assert ok.data["estimated_cost"] == 100.0  # 200 km / 12 km/l * 6

        distance = await manager.call_tool(
            SERVER,
            "calculate_distance",
            {
                "origin": {"latitude": -22.21, "longitude": -49.94},
                "destination": {"latitude": -22.21, "longitude": -49.65},
            },
        )
        assert distance.ok and 29 < distance.data["straight_line_km"] < 31

        invalid = await manager.call_tool(SERVER, "calculate_fuel_cost", {"distance_km": "x"})
        assert not invalid.ok and "inválidos" in (invalid.error or "")

        unknown = await manager.call_tool(SERVER, "drop_tables", {})
        assert not unknown.ok and "não permitida" in (unknown.error or "")

        unavailable = await manager.call_tool("broken", "anything", {})
        assert not unavailable.ok
    finally:
        await manager.stop()
