import logging


def configure_logging():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("passlib").setLevel(logging.ERROR)
