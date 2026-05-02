import sys
import dramatiq

from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import LINK_PROCESSOR_QUEUE, LINK_PROCESSOR_ACTOR
from laws_agent.clients.queue.process_link_payload import ProcessLinkSourcePayload
from laws_agent.parsers.config_parser import parse_sources_config


def ensure_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def main(config_path: str, broker=None) -> None:
    if broker is None:
        broker = QueueClient().create("job")
        dramatiq.set_broker(broker)

    sources_config = parse_sources_config(config_path)

    for group in sources_config.groups:
        for source in group.sources:
            url = ensure_scheme(source.link)
            payload = ProcessLinkSourcePayload(url=url, group=group.name)
            broker.enqueue(
                dramatiq.Message(
                    queue_name=LINK_PROCESSOR_QUEUE,
                    actor_name=LINK_PROCESSOR_ACTOR,
                    args=[],
                    kwargs=payload.to_actor_kwargs(),
                    options={},
                  
                )
            )
            print(f"Enqueued {url} for group {group.name!r}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <config_path>")
        sys.exit(1)
    main(sys.argv[1])
