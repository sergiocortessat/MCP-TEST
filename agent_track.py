"""Agente mínimo: llama a tu MCP y deja la traza en LangSmith.

Cómo funciona (versión junior):
1. LangSmith se activa solo con variables de entorno (LANGSMITH_TRACING=true).
2. MCPAdapter lee las tools de tu servidor MCP (Railway).
3. create_agent + Ollama (llama3.2) decide si llamar esas tools.
4. En la consola imprimimos qué tools se llamaron; en LangSmith lo ves en árbol.

Uso:
    cp .env.example .env   # rellena LANGSMITH_API_KEY
    # Asegúrate de que Ollama está corriendo: ollama serve
    uv run python agent_track.py
    # o con pregunta propia:
    uv run python agent_track.py "Lista los contactos"
"""

from __future__ import annotations

import asyncio
import os
import sys
import warnings
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import AIMessage, ToolMessage
from langchain_ollama import ChatOllama

# langchain.mcp aún está en beta; silenciamos el aviso para no confundir.
warnings.filterwarnings("ignore", message=".*langchain.mcp.*")
from langchain.mcp import MCPAdapter  # noqa: E402

load_dotenv()

# URL de tu MCP en Railway (la misma que en .cursor/mcp.json)
MCP_URL = os.getenv(
    "MCP_URL",
    "https://mcp-test-production-303973cb.up.railway.app/mcp",
)

# Ollama local. En .env puedes poner "llama3.2" o "ollama:llama3.2".
_raw_model = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_MODEL_NAME = _raw_model.removeprefix("ollama:")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

PREGUNTA_POR_DEFECTO = (
    "Lista todos los contactos del MCP. Usa la herramienta listar_contactos."
)


def _ollama_alive() -> bool:
    try:
        with urlopen(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=2) as resp:
            return 200 <= resp.status < 300
    except (URLError, TimeoutError, OSError):
        return False


def _check_env() -> None:
    missing = []
    if not os.getenv("LANGSMITH_API_KEY"):
        missing.append("LANGSMITH_API_KEY")
    if os.getenv("LANGSMITH_TRACING", "").lower() not in {"1", "true", "yes"}:
        missing.append("LANGSMITH_TRACING=true")

    if missing:
        print("❌ Falta configurar el entorno:")
        for item in missing:
            print(f"   - {item}")
        print("\nCopia .env.example a .env y rellena los valores.")
        print("LangSmith API key: https://smith.langchain.com → Settings → API Keys")
        raise SystemExit(1)

    if not _ollama_alive():
        print(f"❌ Ollama no responde en {OLLAMA_BASE_URL}")
        print("   Arráncalo con: ollama serve")
        print("   Y comprueba el modelo: ollama list  (debe aparecer llama3.2)")
        raise SystemExit(1)


def _imprimir_tracking(messages: list) -> list[str]:
    """Imprime en consola cada llamada a tool MCP (lo mismo que verás en LangSmith)."""
    llamadas: list[str] = []
    print("\n" + "=" * 60)
    print("TRACKING LOCAL (lo que el agente hizo)")
    print("=" * 60)

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                nombre = call["name"]
                args = call.get("args", {})
                llamadas.append(nombre)
                print(f"\n🔧 Tool MCP llamada: {nombre}")
                print(f"   args: {args}")

        if isinstance(msg, ToolMessage):
            contenido = msg.content
            if isinstance(contenido, str) and len(contenido) > 300:
                contenido = contenido[:300] + "…"
            print(f"   ✅ resultado ({msg.name}): {contenido}")

    if not llamadas:
        print("\n⚠️  El agente NO llamó a ninguna tool del MCP.")
        print("    En LangSmith verás solo LLM calls, sin spans de tipo 'tool'.")
    else:
        print(f"\n📌 Tools MCP usadas: {llamadas}")

    print("=" * 60)
    return llamadas


async def main(pregunta: str) -> None:
    _check_env()

    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    agent_id = os.getenv("LANGSMITH_AGENT_ID", "")
    workspace = os.getenv("LANGSMITH_WORKSPACE_ID", "")
    project = os.getenv("LANGSMITH_PROJECT", "")
    destino = f"agente «{agent_id}»" if agent_id else f"proyecto «{project or 'default'}»"

    print(f"MCP URL:     {MCP_URL}")
    print(f"Modelo:      ollama:{OLLAMA_MODEL_NAME}  ({OLLAMA_BASE_URL})")
    print(f"LangSmith:   {endpoint}")
    print(f"Destino LS:  {destino}")
    if workspace:
        print(f"Workspace:   {workspace}")
    print(f"Pregunta:    {pregunta}\n")
    print("Conectando al MCP y descubriendo tools…")

    llm = ChatOllama(
        model=OLLAMA_MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    async with MCPAdapter(MCP_URL) as adapter:
        tools = await adapter.list_tools()
        nombres = [t.name for t in tools]
        print(f"Tools del MCP encontradas: {nombres}\n")

        # create_agent + tools MCP = Ollama decide si llamarlas.
        # LangSmith traza automáticamente cada LLM call y cada tool call.
        agent = create_agent(
            llm,
            tools,
            system_prompt=(
                "Eres un asistente de outreach. Cuando te pidan contactos o datos "
                "del CRM, SIEMPRE usa las herramientas MCP disponibles "
                "(listar_contactos, buscar_contacto, cambiar_estado). "
                "No inventes datos."
            ),
        )

        print("Ejecutando agente (Ollama puede tardar unos segundos)…\n")
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": pregunta}]},
        )

        llamadas = _imprimir_tracking(result["messages"])

        ultima = result["messages"][-1]
        print("\n💬 Respuesta final del agente:")
        print(getattr(ultima, "content", ultima))

        print("\n👀 Ver traza VISUAL en LangSmith:")
        if "eu.api" in endpoint and agent_id and workspace:
            print(
                f"   https://eu.smith.langchain.com/o/{workspace}/a/{agent_id}"
            )
        elif "eu.api" in endpoint:
            print("   https://eu.smith.langchain.com → Tracing")
        else:
            print("   https://smith.langchain.com → Tracing")
        print("   Abre el run más reciente. Busca spans de tipo 'tool'.")
        if llamadas:
            print(f"   Deberías ver: {', '.join(llamadas)}")


if __name__ == "__main__":
    pregunta = " ".join(sys.argv[1:]).strip() or PREGUNTA_POR_DEFECTO
    asyncio.run(main(pregunta))
