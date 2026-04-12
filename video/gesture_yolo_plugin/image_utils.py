from __future__ import annotations

import base64
import binascii

import cv2
import numpy as np


def decode_image_from_base64(image_b64: str, *, max_image_bytes: int) -> np.ndarray:
    payload = image_b64.strip()
    if payload.startswith("data:"):
        _, _, payload = payload.partition(",")

    if not payload:
        raise ValueError("image_b64 is empty.")

    try:
        binary = base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("image_b64 is not valid base64 content.") from exc

    if len(binary) > max_image_bytes:
        raise ValueError(f"image payload exceeds MAX_IMAGE_BYTES={max_image_bytes}.")

    image_array = np.frombuffer(binary, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("failed to decode image from base64 content.")
    return image


def resize_for_edge(image: np.ndarray, *, max_image_side: int) -> np.ndarray:
    height, width = image.shape[:2]
    longest_side = max(height, width)
    if longest_side <= max_image_side:
        return image

    scale = max_image_side / float(longest_side)
    resized_width = max(1, int(round(width * scale)))
    resized_height = max(1, int(round(height * scale)))
    return cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_AREA)
