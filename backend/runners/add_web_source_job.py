import sys
import dramatiq

from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import CRAWL_FRONTIER_MANAGER_QUEUE, CRAWL_FRONTIER_MANAGER_ACTOR
from backend.shared.clients.queue.process_link_payload import ProcessLinkSourcePayload
from backend.shared.parsers.config_parser import parse_sources_config
from backend.shared.pipeline.run_config import build_pipeline_run
from backend.shared.storage.sql.sql_store import SqlStore


def ensure_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def main(config_path: str, broker=None, store=None) -> None:
    if broker is None:
        broker = QueueClient().create("job")
        dramatiq.set_broker(broker)
    if store is None:
        store = SqlStore(application_name="add_web_source_job")

    sources_config = parse_sources_config(config_path)

    for group in sources_config.groups:
        # Record this group's launch config (from the file's settings, env as
        # fallback) before seeding, so the run row exists when the actors run.
        store.pipeline_runs.ensure_for_group(
            build_pipeline_run(
                group=group.name, source_type="web", settings=group.settings
            )
        )

        for source in group.sources:
            url = ensure_scheme(source.link)
            payload = ProcessLinkSourcePayload(url=url, group=group.name)
            broker.enqueue(
                dramatiq.Message(
                    queue_name=CRAWL_FRONTIER_MANAGER_QUEUE,
                    actor_name=CRAWL_FRONTIER_MANAGER_ACTOR,
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
