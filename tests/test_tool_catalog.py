from meu_passeio.modules.mcp.tool_catalog import ToolCatalog, ToolDefinition

SCHEMA = {
    "type": "object",
    "properties": {"days": {"type": "integer", "minimum": 1}},
    "required": ["days"],
}


def _catalog() -> ToolCatalog:
    catalog = ToolCatalog()
    catalog.replace(
        [
            ToolDefinition("budget", "calculate_budget_breakdown", "Distribui orçamento", SCHEMA),
            ToolDefinition("places", "search_places", "Busca lugares", {"type": "object"}),
        ]
    )
    return catalog


def test_validate_arguments():
    tool = _catalog().get("budget__calculate_budget_breakdown")
    assert tool is not None
    assert tool.validate_arguments({"days": 2}) is None
    error = tool.validate_arguments({"days": 0})
    assert error and "days" in error


def test_get_by_parts_and_public_view():
    tool = _catalog().get_by_parts("places", "search_places")
    assert tool is not None
    view = tool.public_view()
    assert view["name"] == "places__search_places"
    assert view["server"] == "places"
