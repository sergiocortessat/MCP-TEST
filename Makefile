# Atajos para el servidor MCP. Ejecutar desde la raíz del proyecto.

UV := $(or $(shell command -v uv 2>/dev/null),$(HOME)/.local/bin/uv)

.PHONY: help sync mcp-dev mcp-run mcp-http

help:
	@echo "make sync      — uv sync (crea/actualiza .venv desde pyproject.toml)"
	@echo "make mcp-dev   — MCP Inspector en el navegador (necesita npx)"
	@echo "make mcp-run   — arranca el servidor por stdio (lo usa Cursor)"
	@echo "make mcp-http  — arranca el servidor por HTTP en http://127.0.0.1:8000/mcp"

sync:
	$(UV) sync

mcp-dev:
	$(UV) run mcp dev server.py

mcp-run:
	$(UV) run mcp run server.py

mcp-http:
	MCP_TRANSPORT=streamable-http PORT=8000 $(UV) run python server.py
