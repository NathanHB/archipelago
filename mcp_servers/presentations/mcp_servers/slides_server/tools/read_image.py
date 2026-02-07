import base64

from fastmcp.utilities.types import Image
from utils.decorators import make_async_background
from utils.image_cache import IMAGE_CACHE


@make_async_background
def read_image(file_path: str, annotation: str) -> Image:
    """Retrieve a cached image extracted by read_slide using its annotation key."""
    if not isinstance(file_path, str) or not file_path:
        raise ValueError("File path is required and must be a string")

    if not isinstance(annotation, str) or not annotation:
        raise ValueError("Annotation is required and must be a string")

    # Normalize path to match read_individualslide behavior (must start with /)
    if not file_path.startswith("/"):
        file_path = "/" + file_path

    # Strip leading @ if present (in case output formatting adds it as a prefix)
    clean_annotation = annotation.lstrip("@")

    # Validate annotation is not empty after stripping
    if not clean_annotation:
        raise ValueError("Annotation cannot be empty or contain only '@' characters")

    cache_key = f"{file_path}::{clean_annotation}"

    if cache_key not in IMAGE_CACHE:
        raise ValueError(
            f"Image not found in cache for file '{file_path}' with annotation '{clean_annotation}'. "
            "Make sure you've called read_individualslide first to extract images."
        )

    try:
        base64_data = IMAGE_CACHE.get(cache_key)

        if not base64_data or len(base64_data) == 0:
            raise ValueError("Image data is empty")

        image_bytes = base64.b64decode(base64_data)
        return Image(data=image_bytes, format="jpeg")

    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to read image from cache: {repr(exc)}") from exc
