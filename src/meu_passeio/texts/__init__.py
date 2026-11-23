"""Textos do projeto, centralizados por área.

Este pacote contém SOMENTE textos: instruções dos MCP Servers, descrições de tools,
parâmetros e campos, notas, mensagens de erro e mensagens da API. O código importa daqui;
para revisar ou traduzir qualquer texto, edite apenas estes arquivos.

Mensagens com ``{placeholders}`` são formatadas com ``str.format`` no ponto de uso.

- ``common``  — erros compartilhados pelos MCP Servers (provedores, tools)
- ``places``  — Places MCP Server
- ``maps``    — Maps MCP Server
- ``weather`` — Weather MCP Server
- ``budget``  — Budget MCP Server
- ``shared``  — campos dos schemas de domínio (TripPlan etc.)
- ``api``     — API FastAPI e MCP Client Manager
"""
