import logging


def setup_logging(verbose: bool) -> None:
    """
    Configure root logging for the copernicus command-line tools.
    """
    level = logging.DEBUG if verbose else logging.INFO

    fmt = logging.Formatter
    formatter = fmt("[%(name)-15s] %(levelname)-8s: %(message)s") if verbose else fmt("%(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root_logger.handlers = [console]

    # reduce chatter from dependencies
    logging.getLogger("pydasi").setLevel(logging.WARNING)
    logging.getLogger("utils").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    if verbose:
        logging.getLogger("pystac").setLevel(logging.DEBUG)
        logging.getLogger("pystac_client").setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
