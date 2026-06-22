import asyncio

from laws_agent.agent.config import LLMProvider
from laws_agent.agent.graph import build_agent
from laws_agent.agent.input_processor import init_by_input


async def run(prompt: str, provider: LLMProvider, model: str) -> str:
    agent = await build_agent(provider, model)
    result = await agent.ainvoke({"question": prompt, "search_count": 0, "chunks": []})
    return result["answer"]


def main() -> None:
    prompt, provider, model = init_by_input()

    print(asyncio.run(run(prompt, provider, model)))


if __name__ == "__main__":
    main()
