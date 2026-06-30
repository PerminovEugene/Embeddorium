from langchain_openai import ChatOpenAI

from backend.agent.config import OPENAI_API_KEY, OPENAI_MODEL


def build_openai_llm() -> ChatOpenAI:
    return ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY or None)
