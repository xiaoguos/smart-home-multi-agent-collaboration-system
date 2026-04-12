# Gesture YOLO Plugin

Standalone YOLO-based gesture recognition plugin designed for edge deployment.
This module is intentionally decoupled from the existing MOSS runtime.

## Features

- YOLO inference for gesture detection or classification.
- Incremental gesture learning without full retraining.
- Local SQLite storage by default (configured via `.env`).
- FastAPI endpoints for recognition, learning, and label management.
- CPU-first defaults for low-power edge devices.

## Directory

```text
gesture_yolo_plugin/
  __main__.py
  config.py
  engine.py
  image_utils.py
  schemas.py
  service.py
  storage.py
  .env.example
  pyproject.toml
```

## Quick Start (uv)

```bash
cd video/gesture_yolo_plugin
cp .env.example .env
uv sync
uv run .
```

The service starts on `http://0.0.0.0:12100` by default.

## API

- `GET /healthz`
- `POST /v1/recognize`
- `POST /v1/learn`
- `GET /v1/labels`
- `DELETE /v1/labels/{label}`

### Sample request: recognize

```json
{
  "image_b64": "data:image/jpeg;base64,...",
  "top_k": 3
}
```

### Sample request: learn

```json
{
  "label": "thumbs_up",
  "image_b64": "data:image/jpeg;base64,...",
  "source": "camera-01"
}
```

## Edge Deployment Notes

- Keep `YOLO_DEVICE=cpu` unless your edge board has CUDA.
- Use a small model (`yolo11n` family or a compact custom gesture model).
- Reduce `MAX_IMAGE_SIDE` to reduce latency and memory pressure.
- Keep `MAX_SAMPLES_PER_LABEL` bounded to control storage growth.
- Use local SQLite to avoid network round-trips on edge nodes.
