"""Seed runner for the local-file (XML) ingestion chain.

Reads a sources config file, enumerates every ``*.xml`` file under each
``type: "xml"`` source's ``path``, and publishes one
``ProcessFileSourcePayload`` message per file to ``fetch_file_source``. Run it
after the file-chain workers and the outbox dispatcher are up.
"""

import sys
from pathlib import Path

import dramatiq

from laws_agent.clients.queue.process_file_payload import ProcessFileSourcePayload
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import (
    FETCH_FILE_SOURCE_ACTOR,
    FETCH_FILE_SOURCE_QUEUE,
)
from laws_agent.parsers.config_parser import parse_sources_config


def main(config_path: str, broker=None) -> None:
    if broker is None:
        broker = QueueClient().create("job")
        dramatiq.set_broker(broker)

    sources_config = parse_sources_config(config_path)

    for group in sources_config.groups:
        for source in group.sources:
            if source.type != "xml":
                continue

            file_paths = sorted(Path(source.path).glob(source.glob))
            for file_path in file_paths:
                payload = ProcessFileSourcePayload(
                    file_path=str(file_path), group=group.name
                )
                broker.enqueue(
                    dramatiq.Message(
                        queue_name=FETCH_FILE_SOURCE_QUEUE,
                        actor_name=FETCH_FILE_SOURCE_ACTOR,
                        args=[],
                        kwargs=payload.to_actor_kwargs(),
                        options={},
                    )
                )

            print(
                f"Enqueued {len(file_paths)} files for group {group.name!r} "
                f"from {source.path}"
            )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <config_path>")
        sys.exit(1)
    main(sys.argv[1])
