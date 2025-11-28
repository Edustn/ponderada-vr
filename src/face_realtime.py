from __future__ import annotations

import cv2
import os
from dotenv import load_dotenv
from mqtt_publisher import MQTTConnectionParams, MQTTPublisher
from recognition import (
    SIMILARITY_THRESHOLD,
    FaceRecognitionEngine,
    draw_box,
    get_reference_embedding,
    load_face_analyzer,
    resolve_reference_dir,
)

load_dotenv()


BROKER = "2c1d3753ae2245788f10b12911914b34.s1.eu.hivemq.cloud"
PORT = 8883
TOPIC = "cecilia_vr"
CLIENT_ID = "cecilia_ponderada"
USERNAME = os.getenv("USERNAME_POND")
PASSWORD = os.getenv("PASSWORD")


def create_publisher() -> MQTTPublisher:
    params = MQTTConnectionParams(
        host=BROKER,
        port=PORT,
        client_id=CLIENT_ID,
        username=USERNAME,
        password=PASSWORD,
        keepalive=60,
        use_tls=True,
    )
    publisher = MQTTPublisher(params, TOPIC)
    publisher.connect()
    return publisher


def main() -> None:
    ref_dir = resolve_reference_dir()
    analyzer = load_face_analyzer()
    ref_emb = get_reference_embedding(analyzer, ref_dir)
    print(f"Embeddings de referência prontas a partir de {ref_dir}")

    recognizer = FaceRecognitionEngine(analyzer, ref_emb, SIMILARITY_THRESHOLD)
    publisher = create_publisher()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        publisher.close()
        raise SystemExit("Não consegui abrir a câmera.")

    print("Pressione 'q' para sair.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Falha ao ler frame da câmera.")
                break

            results = recognizer.process_frame(frame)
            for result in results:
                payload = "1" if result.is_target else "0"
                try:
                    publisher.publish(payload)
                except RuntimeError as err:
                    print(f"[mqtt] {err}")
                draw_box(frame, result)

            cv2.imshow("InsightFace - Real Time", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        publisher.close()


if __name__ == "__main__":
    main()
