from pathlib import Path
from typing import Iterable, List, Tuple

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from dotenv import load_dotenv
import os

load_dotenv()


IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
DEFAULT_REF_DIR = Path(os.getenv("DEFAULT_REF_DIR"))
CACHE_FILENAME = Path(os.getenv("CACHE_FILENAME"))


def load_face_analyzer() -> FaceAnalysis:
    # Usa CPU por padrão; troque providers para GPU se disponível.
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


def get_largest_face_embedding(app: FaceAnalysis, image_bgr: np.ndarray) -> np.ndarray | None:
    """Retorna embedding da maior face na imagem (ou None)."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    faces = app.get(rgb)
    if not faces:
        return None
    face = max(faces, key=lambda f: f.det_score)
    emb = face["embedding"]
    # Normaliza para cos similarity.
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


def draw_box(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    label: str,
    score: float,
    color: Tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = map(int, bbox)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    text = f"{label}: {score:.2f}"
    cv2.putText(
        frame,
        text,
        (x1, max(y1 - 10, 0)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2,
        cv2.LINE_AA,
    )


def main() -> None:

    app = load_face_analyzer()
    if not DEFAULT_REF_DIR.exists():
        raise SystemExit(f"Pasta de referência não existe: {DEFAULT_REF_DIR}")

    ref_emb = get_reference_embedding(app, DEFAULT_REF_DIR)
    print(f"Embeddings de referência prontas a partir de {DEFAULT_REF_DIR}")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("Não consegui abrir a câmera.")

    print("Pressione 'q' para sair.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Falha ao ler frame da câmera.")
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = app.get(rgb)
        for face in faces:
            emb = face["embedding"]
            emb = emb / np.linalg.norm(emb)
            sim = float(np.dot(emb, ref_emb))
            if sim >= 0.35:
                color = (0, 200, 0)
                lbl = "target"
            else:
                color = (0, 0, 200)
                lbl = "desconhecido"
            bbox = face.bbox.astype(int).tolist()
            draw_box(frame, bbox, lbl, sim, color)

        cv2.imshow("InsightFace - Real Time", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
