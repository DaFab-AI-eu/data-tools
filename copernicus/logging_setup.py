import logging


def setup_logging(verbose: bool) -> None:
    """
    Configure root logging for the copernicus command-line tools.
    """
    log_format = "[%(name)-15s] %(levelname)-8s: %(message)s" if verbose else "%(message)s"

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(log_format))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    root_logger.handlers = [console]

    if not verbose:
        for name in ("utils", "boto3", "botocore", "pystac", "pystac_client", "requests", "urllib3"):
            logging.getLogger(name).setLevel(logging.WARNING)
