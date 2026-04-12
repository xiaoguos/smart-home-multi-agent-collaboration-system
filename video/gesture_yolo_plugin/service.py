from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

from fastapi import FastAPI, HTTPException

from config import Settings, load_settings
from engine import YoloGestureEngine
from image_utils import decode_image_from_base64, resize_for_edge
from schemas import (
    Candidate,
    HealthResponse,
    LabelEntry,
    LabelsResponse,
    LearnRequest,
    LearnResponse,
    RecognizeRequest,
    RecognizeResponse,
)
from storage import GestureLearningStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Runtime:
    settings: Settings
    store: GestureLearningStore
    engine: YoloGestureEngine


def _configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@lru_cache(maxsize=1)
def get_runtime() -> Runtime:
    settings = load_settings()
    _configure_logging(settings.log_level)
    store = GestureLearningStore(settings.sqlite_path)
    engine = YoloGestureEngine(settings=settings, store=store)
    return Runtime(settings=settings, store=store, engine=engine)


def _decode_edge_image(image_b64: str) -> tuple[Runtime, object]:
    runtime = get_runtime()
    decoded = decode_image_from_base64(
        image_b64=image_b64,
        max_image_bytes=runtime.settings.max_image_bytes,
    )
    resized = resize_for_edge(decoded, max_image_side=runtime.settings.max_image_side)
    return runtime, resized


app = FastAPI(
    title="Gesture YOLO Plugin",
    version="0.1.0",
    description="Standalone YOLO gesture recognition service with incremental learning.",
)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    runtime = get_runtime()
    return HealthResponse(
        status="ok",
        model_path=runtime.settings.yolo_model_path,
        learning_enabled=runtime.settings.learning_enabled,
    )


@app.post("/v1/recognize", response_model=RecognizeResponse)
def recognize(payload: RecognizeRequest) -> RecognizeResponse:
    try:
        runtime, image = _decode_edge_image(payload.image_b64)
        result = runtime.engine.recognize(image=image, top_k=payload.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - protective boundary
        logger.exception("recognize request failed")
        raise HTTPException(status_code=500, detail="internal error during recognition") from exc

    return RecognizeResponse(
        label=result.label,
        score=result.score,
        source=result.source,
        model_label=result.model_label,
        model_score=result.model_score,
        candidates=[
            Candidate(label=item.label, score=item.score, source=item.source)
            for item in result.candidates
        ],
    )


@app.post("/v1/learn", response_model=LearnResponse)
def learn(payload: LearnRequest) -> LearnResponse:
    try:
        runtime, image = _decode_edge_image(payload.image_b64)
        result = runtime.engine.learn(label=payload.label, image=image, source=payload.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - protective boundary
        logger.exception("learn request failed")
        raise HTTPException(status_code=500, detail="internal error during learning") from exc

    return LearnResponse(
        label=result.label,
        sample_count=result.sample_count,
        model_hint_label=result.model_hint_label,
        model_hint_score=result.model_hint_score,
    )


@app.get("/v1/labels", response_model=LabelsResponse)
def labels() -> LabelsResponse:
    runtime = get_runtime()
    items = runtime.store.list_labels()
    return LabelsResponse(
        labels=[LabelEntry(label=item.label, sample_count=item.sample_count) for item in items]
    )


@app.delete("/v1/labels/{label}", response_model=LabelEntry)
def delete_label(label: str) -> LabelEntry:
    normalized = label.strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="label cannot be empty")
    runtime = get_runtime()
    deleted = runtime.store.delete_label(normalized)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="label not found")
    return LabelEntry(label=normalized, sample_count=0)


@app.on_event("shutdown")
def close_runtime() -> None:
    try:
        runtime = get_runtime()
    except Exception:
        return
    runtime.store.close()
