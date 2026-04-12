from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _as_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _as_int(raw_value: str | None, default: int, *, minimum: int) -> int:
    if raw_value in (None, ""):
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(parsed, minimum)


def _as_float(raw_value: str | None, default: float, *, minimum: float, maximum: float) -> float:
    if raw_value in (None, ""):
        return default
    try:
        parsed = float(raw_value)
    except ValueError:
        return default
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


@dataclass(frozen=True, slots=True)
class Settings:
    service_host: str
    service_port: int
    log_level: str
    yolo_model_path: str
    yolo_device: str
    yolo_confidence: float
    max_image_side: int
    max_image_bytes: int
    learning_enabled: bool
    gesture_db_url: str
    similarity_threshold: float
    min_samples_per_label: int
    max_samples_per_label: int

    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.gesture_db_url.startswith(prefix):
            raise ValueError("Only sqlite:/// URLs are supported for this plugin.")
        raw_path = self.gesture_db_url[len(prefix) :]
        if not raw_path:
            raise ValueError("GESTURE_DB_URL must include a file path.")
        return Path(raw_path).expanduser()


def load_settings() -> Settings:
    load_dotenv(override=False)

    service_host = os.getenv("SERVICE_HOST", "0.0.0.0").strip() or "0.0.0.0"
    service_port = _as_int(os.getenv("SERVICE_PORT"), 12100, minimum=1)
    log_level = (os.getenv("LOG_LEVEL", "INFO").strip() or "INFO").upper()

    yolo_model_path = os.getenv("YOLO_MODEL_PATH", "./models/gesture.pt").strip() or "./models/gesture.pt"
    yolo_device = os.getenv("YOLO_DEVICE", "cpu").strip() or "cpu"
    yolo_confidence = _as_float(os.getenv("YOLO_CONFIDENCE"), 0.25, minimum=0.01, maximum=0.99)
    max_image_side = _as_int(os.getenv("MAX_IMAGE_SIDE"), 960, minimum=128)
    max_image_bytes = _as_int(os.getenv("MAX_IMAGE_BYTES"), 6 * 1024 * 1024, minimum=64 * 1024)

    learning_enabled = _as_bool(os.getenv("LEARNING_ENABLED"), True)
    gesture_db_url = (
        os.getenv("GESTURE_DB_URL", "sqlite:///./data/gesture_learning.db").strip()
        or "sqlite:///./data/gesture_learning.db"
    )
    if not gesture_db_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// URLs are supported for edge deployment.")
    similarity_threshold = _as_float(os.getenv("SIMILARITY_THRESHOLD"), 0.82, minimum=0.1, maximum=0.99)
    min_samples_per_label = _as_int(os.getenv("MIN_SAMPLES_PER_LABEL"), 3, minimum=1)
    max_samples_per_label = _as_int(os.getenv("MAX_SAMPLES_PER_LABEL"), 200, minimum=min_samples_per_label)

    return Settings(
        service_host=service_host,
        service_port=service_port,
        log_level=log_level,
        yolo_model_path=yolo_model_path,
        yolo_device=yolo_device,
        yolo_confidence=yolo_confidence,
        max_image_side=max_image_side,
        max_image_bytes=max_image_bytes,
        learning_enabled=learning_enabled,
        gesture_db_url=gesture_db_url,
        similarity_threshold=similarity_threshold,
        min_samples_per_label=min_samples_per_label,
        max_samples_per_label=max_samples_per_label,
    )
