# MCP-TEST

Servidor MCP de ejemplo (outreach) + un agente mínimo con **LangChain + LangSmith** para ver, de forma visual, cuándo el agente llama de verdad a tus tools MCP.

## ¿Qué estamos midiendo?

```
Tú → agente (LangChain) → tools del MCP (Railway)
                ↓
         LangSmith (trazas)
```

Si el agente llama `listar_contactos`, en LangSmith verás un span de tipo **tool**.  
Si responde de memoria sin tool, solo verás llamadas al LLM.

## 1. Tracking visual (lo más útil si eres junior)

### Preparar entorno

1. Ollama corriendo con llama 3.2:

```bash
ollama serve          # si no está ya en marcha
ollama pull llama3.2  # solo la primera vez
```

2. LangSmith (solo para ver las trazas):

```bash
cp .env.example .env
```

Edita `.env` y pon:

| Variable | Dónde sacarla |
|---|---|
| `LANGSMITH_API_KEY` | https://smith.langchain.com → Settings → API Keys |
| `LANGSMITH_TRACING=true` | Activa el envío de trazas |
| `LANGSMITH_PROJECT` | Nombre del proyecto en LangSmith (ej. `mcp-outreach-demo`) |
| `OLLAMA_MODEL` | Por defecto `llama3.2` (local, sin API key) |

### Ejecutar el agente

```bash
uv sync
uv run python agent_track.py
```

O con otra pregunta:

```bash
uv run python agent_track.py "Busca el contacto de Ana"
```

### Qué verás

**En la terminal:** un bloque `TRACKING LOCAL` con las tools MCP llamadas (`listar_contactos`, etc.).

**En LangSmith (visual):**

1. Entra en https://smith.langchain.com  
2. Abre el proyecto `mcp-outreach-demo`  
3. Ve a **Tracing** y abre el run más reciente  
4. En el árbol deberías ver algo como:

```
agent
├── ChatOllama          ← llama3.2 decide
└── listar_contactos    ← ¡esta es la llamada real a tu MCP!
```

Ese span `listar_contactos` es la prueba de que el agente usó tu MCP.

## 2. Servidor MCP (local / Railway)

```bash
# Local (stdio, para Cursor)
uv run python server.py

# HTTP (como en Railway)
MCP_TRANSPORT=streamable-http uv run python server.py
```

Tools: `listar_contactos`, `buscar_contacto`, `cambiar_estado`.  
Resource: `outreach://estados`.  
Prompt: `redactar_email`.
