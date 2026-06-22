from langchain_ollama import ChatOllama

from laws_agent.agent.config import OLLAMA_BASE_URL, OLLAMA_MODEL


def build_ollama_llm(model: str | None) -> ChatOllama:
    return ChatOllama(model=model if model is not None else OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
