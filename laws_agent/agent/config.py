from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

LLMProvider = Literal["ollama", "openai"]

# Agent
LLM_PROVIDER: LLMProvider = os.getenv("LLM_PROVIDER", "ollama")  # type: ignore[assignment]

# MCP
MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Ollama
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
