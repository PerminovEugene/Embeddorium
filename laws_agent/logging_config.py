import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level)
    root.addHandler(handler)

    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("dramatiq").setLevel(logging.INFO)
