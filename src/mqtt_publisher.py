"""Utilitário reutilizável para publicar mensagens MQTT com TLS opcional."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

import paho.mqtt.client as mqtt


@dataclass
class MQTTConnectionParams:
    host: str
    port: int = 1883
    client_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    keepalive: int = 60
    use_tls: bool = False
    ca_cert: Optional[str] = None
    connect_timeout: float = 5.0


class MQTTPublisher:
    """Pequeno wrapper em volta do paho-mqtt voltado para publishes."""

    def __init__(self, params: MQTTConnectionParams, topic: str) -> None:
        if not topic:
            raise ValueError("O tópico MQTT não pode ser vazio.")
        self.params = params
        self.topic = topic
        self._connected = threading.Event()
        self._client = mqtt.Client(
            client_id=params.client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        if params.username:
            self._client.username_pw_set(params.username, params.password)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def connect(self) -> None:
        params = self.params
        if params.use_tls:
            # Usa o CA fornecido ou o store padrão do sistema.
            self._client.tls_set(ca_certs=params.ca_cert)
        self._client.connect(params.host, params.port, params.keepalive)
        self._client.loop_start()
        if not self._connected.wait(timeout=params.connect_timeout):
            raise RuntimeError("MQTT: conexão não estabelecida dentro do timeout.")

    def publish(self, payload: str, qos: int = 1, retain: bool = False) -> None:
        if not self._connected.is_set():
            raise RuntimeError("MQTT: é preciso estar conectado antes de publicar.")
        result = self._client.publish(self.topic, payload=payload, qos=qos, retain=retain)
        rc = result.rc
        if rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT: publish falhou com código {rc}.")

    def close(self) -> None:
        if not self._connected.is_set():
            return
        self._client.loop_stop()
        self._client.disconnect()
        self._connected.clear()

    # --- Callbacks internos -------------------------------------------------
    def _on_connect(self, client: mqtt.Client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code == 0:
            self._connected.set()
        else:
            print(f"[mqtt] Falha ao conectar (código {reason_code})")
            self._connected.clear()

    def _on_disconnect(self, client: mqtt.Client, userdata, reason_code, properties=None) -> None:
        if reason_code != 0:
            print(f"[mqtt] Desconectado com código {reason_code}")
        self._connected.clear()
