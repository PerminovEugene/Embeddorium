import sys
from pathlib import Path

from laws_agent.agent.config import LLMProvider


def read_prompt_from_path(prompt_path: str) -> str:
    path = Path(prompt_path)

    if not path.exists():
        raise FileNotFoundError(f"Prompt file does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Prompt path is not a file: {path}")

    return path.read_text(encoding="utf-8")


def init_by_input() -> tuple[str, LLMProvider]:
    if len(sys.argv) < 2:
        print("Usage: python -m laws_agent.agent.generate '<prompt_path>' [ollama|openai]")
        sys.exit(1)

    prompt_path = sys.argv[1]
    provider_raw = sys.argv[2]
    model = sys.argv[3] 

    try:
        provider = LLMProvider(provider_raw)
    except ValueError:
        allowed = ", ".join(p.value for p in LLMProvider)
        print(f"Invalid provider: {provider_raw}. Allowed values: {allowed}")
        sys.exit(1)

    prompt = read_prompt_from_path(prompt_path)

    return prompt, provider, model