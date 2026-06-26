import logging
import sys

from laws_agent.log_routing import install_file_routing


def configure_logging(level: str = "INFO") -> None:
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    root = logging.getLogger()

    # The per-URL file routing handler must be installed even when the root
    # logger was already configured by another framework. The dramatiq CLI
    # configures logging *before* importing actor modules, so by the time this
    # runs in a worker ``root.handlers`` is already populated — guarding the
    # whole function on that (as before) would skip file routing entirely.
    # ``install_file_routing`` is idempotent, so calling it unconditionally is
    # safe across re-imports / reloads.
    install_file_routing(root, formatter)

    has_stream = any(
        isinstance(h, logging.StreamHandler) for h in root.handlers
    )
    if not has_stream:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root.setLevel(level)
        root.addHandler(handler)

    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("dramatiq").setLevel(logging.INFO)
