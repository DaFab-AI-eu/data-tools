import logging


def setup_logging(verbose):
    level = logging.DEBUG if verbose else logging.INFO

    fmt = logging.Formatter
    formatter = fmt('[%(name)-15s] %(levelname)-8s: %(message)s') if verbose else fmt('%(message)s')

    # Configure the root logger so all loggers inherit this handler and level
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.propagate = True

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root_logger.handlers = [console]

    # reduce chatter
    logging.getLogger("pydasi").setLevel(logging.WARNING)
    logging.getLogger("utils").setLevel(logging.WARNING)
    # Set boto3 and botocore loggers to WARNING to
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    if verbose:
        logging.getLogger("pystac").setLevel(logging.DEBUG)
        logging.getLogger("pystac_client").setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        # logging.getLogger("urllib3").setLevel(logging.DEBUG)
        u3_logger = logging.getLogger("urllib3")
        u3_logger.setLevel(logging.DEBUG)
        u3_logger.propagate = True  # Force it to send logs to the root handler


def media_subtype(media_type: str, separator: str = "_") -> str:
    """Extract the subtype from a media type string.

    Args:
        media_type: A media type like 'image_jp2' or 'image/tiff'.
        separator: The separator between type and subtype (default: '_').

    Returns:
        The subtype portion (e.g. 'jp2', 'tiff'), or the original
        string if no separator is found.
    """
    _, _, subtype = media_type.rpartition(separator)
    return subtype or media_type


def log_request(request) -> None:
    method = getattr(request, 'method', 'UNKNOWN')
    url = getattr(request, 'url', 'UNKNOWN')
    print(f"{method} {url}")

    # Log headers if available
    headers = getattr(request, 'headers', {})
    if headers:
        print(f"Headers: {dict(headers)}")

    # Log payload from json attribute (pystac-client uses json for POST data)
    json_data = getattr(request, 'json', None)
    if json_data:
        import json

        print(f"Payload: {json.dumps(json_data, indent=2)}")

    return None
