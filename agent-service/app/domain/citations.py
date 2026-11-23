"""Source label formatting shared by retrieval and response models."""


def source_label(source: str, section: str) -> str:
    """Format a document citation as `archivo.md > Sección`."""

    return f"{source} > {section}"
