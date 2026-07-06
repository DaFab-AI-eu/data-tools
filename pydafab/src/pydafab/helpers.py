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
