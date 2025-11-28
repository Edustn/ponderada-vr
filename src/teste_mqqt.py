import os
import threading

import paho.mqtt.client as mqtt

BROKER = "2c1d3753ae2245788f10b12911914b34.s1.eu.hivemq.cloud"
PORT = 8883  # TLS port for HiveMQ Cloud
TOPIC = "cecilia_vr"
CLIENT_ID = "ponderada-vr-teste"
USERNAME = "cecilia_vr"
PASSWORD = "Inteli@123"

# Usamos um Event para aguardar a conexão antes de publicar.
connected_event = threading.Event()


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("Conectado com sucesso!")
        connected_event.set()
    else:
        print(f"Falha na conexão. Código: {reason_code}")
        connected_event.clear()


def on_publish(client, userdata, mid, reason_code, properties=None):
    print("Mensagem publicada!")


def on_disconnect(client, userdata, reason_code, properties=None):
    if reason_code != 0:
        print(f"Desconectado inesperadamente (código: {reason_code})")
    else:
        print("Desconectado normalmente.")


if PASSWORD is None:
    raise RuntimeError(
        "Defina a variável de ambiente MQTT_PASSWORD com a senha do cluster."
    )

client = mqtt.Client(
    client_id=CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = on_connect
client.on_publish = on_publish
client.on_disconnect = on_disconnect

# Configura TLS (necessário para HiveMQ Cloud) e autenticação
client.tls_set()  # usa a CA padrão do sistema
client.username_pw_set(USERNAME, PASSWORD)

# Conectar ao broker e iniciar o loop de rede em background
client.connect(BROKER, PORT, keepalive=60)
client.loop_start()

# Aguarda a conexão antes de publicar
if not connected_event.wait(timeout=5):
    raise RuntimeError("Não conectou ao broker em 5 segundos.")

# Publicar mensagem
mensagem = "Olá do Thonny via MQTT!"
result = client.publish(TOPIC, mensagem, qos=1)
status = result[0]
if status == mqtt.MQTT_ERR_SUCCESS:
    print(f"Mensagem enviada para o tópico {TOPIC}.")
else:
    print(f"Erro ao publicar: código {status}.")

# Parar loop e desconectar após garantir que callbacks foram processados
client.loop_stop()
# client.disconnect()
