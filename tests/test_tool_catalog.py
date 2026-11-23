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


def test_select_with_wildcard_allowlist():
    names = [t.qualified_name for t in _catalog().select(["budget__*"])]
    assert names == ["budget__calculate_budget_breakdown"]


def test_select_none_returns_all():
    assert len(_catalog().select(None)) == 2


def test_validate_arguments():
    tool = _catalog().get("budget__calculate_budget_breakdown")
    assert tool is not None
    assert tool.validate_arguments({"days": 2}) is None
    error = tool.validate_arguments({"days": 0})
    assert error and "days" in error


def test_llm_tool_shape():
    tool = _catalog().get("places__search_places")
    assert tool is not None
    llm_tool = tool.to_llm_tool()
    assert llm_tool["name"] == "places__search_places"
    assert llm_tool["description"].startswith("[places]")
    assert llm_tool["input_schema"] == {"type": "object"}


def test_split():
    assert ToolCatalog.split("maps__get_route") == ("maps", "get_route")
