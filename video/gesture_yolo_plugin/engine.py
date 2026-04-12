from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from ultralytics import YOLO

from config import Settings
from storage import GestureLearningStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CandidateResult:
    label: str
    score: float
    source: str


@dataclass(frozen=True, slots=True)
class InferenceResult:
    label: str
    score: float
    source: str
    model_label: str
    model_score: float
    candidates: list[CandidateResult]


@dataclass(frozen=True, slots=True)
class LearnResult:
    label: str
    sample_count: int
    model_hint_label: str
    model_hint_score: float


class YoloGestureEngine:
    def __init__(self, settings: Settings, store: GestureLearningStore) -> None:
        self._settings = settings
        self._store = store
        self._model = YOLO(settings.yolo_model_path)
        self._class_names = self._load_class_names()
        logger.info("YOLO model loaded: %s", settings.yolo_model_path)

    def _load_class_names(self) -> dict[int, str]:
        names = getattr(self._model, "names", None)
        if isinstance(names, dict):
            return {int(index): str(name) for index, name in names.items()}
        if isinstance(names, list):
            return {index: str(name) for index, name in enumerate(names)}
        return {}

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-8:
            return vector.astype(np.float32)
        return (vector / norm).astype(np.float32)

    def _class_name(self, class_index: int) -> str:
        return self._class_names.get(class_index, str(class_index))

    def _extract_from_probs(self, result: Any) -> tuple[np.ndarray, str, float] | None:
        probs_obj = getattr(result, "probs", None)
        if probs_obj is None:
            return None
        data = getattr(probs_obj, "data", None)
        if data is None:
            return None

        if hasattr(data, "cpu"):
            probabilities = data.cpu().numpy()
        else:
            probabilities = np.asarray(data)
        probabilities = probabilities.astype(np.float32).reshape(-1)
        if probabilities.size == 0:
            return None

        best_index = int(np.argmax(probabilities))
        best_score = float(probabilities[best_index])
        label = self._class_name(best_index)
        feature_vector = self._normalize(probabilities)
        return feature_vector, label, best_score

    def _extract_from_boxes(self, result: Any) -> tuple[np.ndarray, str, float] | None:
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return None

        cls_raw = getattr(boxes, "cls", None)
        conf_raw = getattr(boxes, "conf", None)
        if cls_raw is None or conf_raw is None:
            return None

        if hasattr(cls_raw, "cpu"):
            classes = cls_raw.cpu().numpy().astype(np.int32)
        else:
            classes = np.asarray(cls_raw, dtype=np.int32)

        if hasattr(conf_raw, "cpu"):
            confidences = conf_raw.cpu().numpy().astype(np.float32)
        else:
            confidences = np.asarray(conf_raw, dtype=np.float32)

        if classes.size == 0 or confidences.size == 0:
            return None

        class_count = (max(self._class_names.keys()) + 1) if self._class_names else int(classes.max()) + 1
        class_count = max(class_count, 1)
        distribution = np.zeros(shape=(class_count,), dtype=np.float32)

        for class_index, confidence in zip(classes, confidences):
            if class_index < 0:
                continue
            if class_index >= distribution.size:
                extension_size = class_index - distribution.size + 1
                distribution = np.pad(distribution, (0, extension_size), mode="constant")
            distribution[class_index] = max(float(confidence), float(distribution[class_index]))

        if float(distribution.max()) <= 0.0:
            return None

        best_index = int(np.argmax(distribution))
        best_score = float(distribution[best_index])
        label = self._class_name(best_index)
        feature_vector = self._normalize(distribution)
        return feature_vector, label, best_score

    def _feature_from_image(self, image: np.ndarray) -> tuple[np.ndarray, str, float]:
        results = self._model.predict(
            source=image,
            conf=self._settings.yolo_confidence,
            device=self._settings.yolo_device,
            verbose=False,
        )
        if not results:
            raise ValueError("YOLO did not return any result.")
        result = results[0]

        probs_extracted = self._extract_from_probs(result)
        if probs_extracted is not None:
            return probs_extracted

        boxes_extracted = self._extract_from_boxes(result)
        if boxes_extracted is not None:
            return boxes_extracted

        raise ValueError("YOLO output does not contain valid probabilities or boxes.")

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))

    def recognize(self, *, image: np.ndarray, top_k: int) -> InferenceResult:
        feature_vector, model_label, model_score = self._feature_from_image(image)
        candidates: list[CandidateResult] = [
            CandidateResult(label=model_label, score=model_score, source="yolo_model")
        ]

        final_label = model_label
        final_score = model_score
        final_source = "yolo_model"

        if self._settings.learning_enabled:
            centroids = self._store.get_label_centroids(
                min_samples_per_label=self._settings.min_samples_per_label
            )
            learned_candidates: list[CandidateResult] = []
            for label, centroid in centroids.items():
                similarity = self._cosine_similarity(feature_vector, centroid)
                learned_candidates.append(
                    CandidateResult(
                        label=label,
                        score=similarity,
                        source="learned_profile",
                    )
                )
            learned_candidates.sort(key=lambda candidate: candidate.score, reverse=True)
            if learned_candidates:
                best_learned = learned_candidates[0]
                if best_learned.score >= self._settings.similarity_threshold:
                    final_label = best_learned.label
                    final_score = best_learned.score
                    final_source = best_learned.source
                candidates.extend(learned_candidates[:top_k])

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return InferenceResult(
            label=final_label,
            score=final_score,
            source=final_source,
            model_label=model_label,
            model_score=model_score,
            candidates=candidates[:top_k],
        )

    def learn(self, *, label: str, image: np.ndarray, source: str) -> LearnResult:
        normalized_label = label.strip().lower()
        if not normalized_label:
            raise ValueError("label cannot be empty.")

        feature_vector, model_label, model_score = self._feature_from_image(image)
        sample_count = self._store.add_sample(
            label=normalized_label,
            feature_vector=feature_vector,
            source=source.strip() or "api",
            max_samples_per_label=self._settings.max_samples_per_label,
        )
        return LearnResult(
            label=normalized_label,
            sample_count=sample_count,
            model_hint_label=model_label,
            model_hint_score=model_score,
        )
