# Instalação e uso no Claude Desktop

[← Voltar ao README](../README.md)

## Instalação

Requer Python 3.11+.

```powershell
git clone https://github.com/otaviosbms/meu-passeio-mcp.git
cd meu-passeio-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Sem a chave do Google, o server já funciona com as alternativas gratuitas; com ela, lugares e
rotas ficam muito mais precisos. Veja [Chave do Google Maps](google-maps.md).

## Usar no Claude Desktop

Adicione o server à configuração de MCP do Claude Desktop (`claude_desktop_config.json`,
acessível em **Configurações → Desenvolvedor → Editar configuração**):

```json
{
  "mcpServers": {
    "meu-passeio": {
      "command": "C:\\caminho\\meu-passeio-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "meu_passeio.mcp_server"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

Reinicie o Claude Desktop (inclusive pela bandeja do Windows). O conector **Meu Passeio** aparece
com as 28 tools e o prompt **Planejar viagem**. Não é preciso deixar nada rodando: o Claude
inicia o server quando precisa. A pasta do projeto e a `.venv` precisam continuar no lugar.

Para testar o server isolado:

```powershell
python -m meu_passeio.mcp_server
```

## Solução de problemas

- **O conector não aparece:** confira o caminho do `python.exe` da `.venv` no JSON e reinicie o
  Claude por completo.
- **Erro em alguma tool:** os logs do Claude Desktop ficam na pasta `logs` dos dados do app
  (arquivos `mcp-server-meu-passeio*.log`).
- **Resultados sem nota nem preço:** o Google não está configurado; o resultado avisa em `notes`.
