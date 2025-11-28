from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import cv2
import numpy as np
from dotenv import load_dotenv
from insightface.app import FaceAnalysis

load_dotenv()

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
CACHE_FILENAME = os.getenv("CACHE_FILENAME", "reference_embedding.npy")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))


@dataclass
class RecognitionResult:
    bbox: Tuple[int, int, int, int]
    similarity: float
    is_target: bool

    @property
    def label(self) -> str:
        return "target" if self.is_target else "desconhecido"

    @property
    def color(self) -> Tuple[int, int, int]:
        return (0, 200, 0) if self.is_target else (0, 0, 200)


def resolve_reference_dir() -> Path:
    ref_dir = os.getenv("DEFAULT_REF_DIR")
    if not ref_dir:
        raise RuntimeError("Defina DEFAULT_REF_DIR no arquivo .env.")
    path = Path(ref_dir)
    if not path.exists():
        raise SystemExit(f"Pasta de referência não existe: {path}")
    return path


def load_face_analyzer() -> FaceAnalysis:
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


class FaceRecognitionEngine:
    def __init__(
        self,
        analyzer: FaceAnalysis,
        reference_embedding: np.ndarray,
        threshold: float,
    ) -> None:
        self.analyzer = analyzer
        self.reference_embedding = reference_embedding
        self.threshold = threshold

    def process_frame(self, frame: np.ndarray) -> List[RecognitionResult]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = self.analyzer.get(rgb)
        results: List[RecognitionResult] = []
        for face in faces:
            emb = face["embedding"]
            emb = emb / np.linalg.norm(emb)
            similarity = float(np.dot(emb, self.reference_embedding))
            bbox = tuple(face.bbox.astype(int).tolist())
            results.append(
                RecognitionResult(
                    bbox=bbox,
                    similarity=similarity,
                    is_target=similarity >= self.threshold,
                )
            )
        return results


def get_largest_face_embedding(app: FaceAnalysis, image_bgr: np.ndarray) -> np.ndarray | None:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    faces = app.get(rgb)
    if not faces:
        return None
    face = max(faces, key=lambda f: f.det_score)
    emb = face["embedding"]
    return emb / np.linalg.norm(emb)


def iter_images(ref_dir: Path) -> Iterable[Path]:
    for path in ref_dir.rglob("*"):
        if path.suffix.lower() in IMAGE_EXTS and path.is_file():
            yield path


def build_reference_embedding(app: FaceAnalysis, ref_dir: Path) -> np.ndarray:
    embeddings: List[np.ndarray] = []
    for img_path in iter_images(ref_dir):
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"[ref] não consegui ler: {img_path}")
            continue
        emb = get_largest_face_embedding(app, img)
        if emb is None:
            print(f"[ref] nenhuma face detectada: {img_path}")
            continue
        embeddings.append(emb)

    if not embeddings:
        raise SystemExit("Nenhuma embedding de referência foi gerada. Verifique a pasta.")

    mean_emb = np.mean(embeddings, axis=0)
    return mean_emb / np.linalg.norm(mean_emb)


def get_reference_embedding(app: FaceAnalysis, ref_dir: Path) -> np.ndarray:
    cache_path = ref_dir / CACHE_FILENAME
    if cache_path.exists():
        print(f"Usando embedding em cache: {cache_path}")
        return np.load(cache_path)

    print("Cache ausente; gerando embeddings de referência pela primeira vez...")
    emb = build_reference_embedding(app, ref_dir)
    np.save(cache_path, emb)
    print(f"Embedding salva em cache: {cache_path}")
    return emb


def draw_box(frame: np.ndarray, result: RecognitionResult) -> None:
    x1, y1, x2, y2 = result.bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), result.color, 2)
    text = f"{result.label}: {result.similarity:.2f}"
    cv2.putText(
        frame,
        text,
        (x1, max(y1 - 10, 0)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        result.color,
        2,
        cv2.LINE_AA,
    )
