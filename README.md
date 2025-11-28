# Reconhecimento facial com acionamento de LED via MQTT

Esse projeto identifica em tempo real um rosto específico usando [InsightFace](https://github.com/deepinsight/insightface). Sempre que a pessoa-alvo está dentro do enquadramento da webcam, o script `src/face_realtime.py` envia o payload `1` para um tópico MQTT; quando o rosto sai de cena, o payload passa a ser `0`. O script `src/pico_mqtt_led.py`, pensado para rodar em um Raspberry Pi Pico W com MicroPython, assina o mesmo tópico e liga/desliga o LED on-board de acordo com essas mensagens.

## Requisitos
- Python 3.10+ com acesso a uma webcam.
- Conta/broker MQTT (o repositório já traz credenciais de exemplo em HiveMQ Cloud, mas troque-as se preferir outra instância).
- Pasta contendo fotos do rosto que deve ser reconhecido.
- (Opcional) Raspberry Pi Pico W com firmware MicroPython 1.20+ para controlar o LED.

## Preparando o ambiente Python
```bash
python -m venv .venv
source .venv/bin/activate  # No Windows use .venv\Scripts\activate
pip install --upgrade pip
pip install -r src/requirements.txt
```

## Configurando as imagens de referência
1. Crie uma pasta com várias fotos bem iluminadas do rosto alvo (opções frontais e laterais melhoram o embedding médio).
2. Anote o caminho absoluto da pasta e crie um arquivo `.env` na raiz do projeto com, pelo menos:
   ```env
   DEFAULT_REF_DIR=/caminho/para/suas/fotos
   SIMILARITY_THRESHOLD=0.35   # ajuste se precisar de mais/menos tolerância
   CACHE_FILENAME=reference_embedding.npy
   ```
3. Na primeira execução, o script gera um `reference_embedding.npy` na pasta de referência para acelerar execuções futuras. Delete-o caso troque as fotos e queira recalcular.

## Executando o reconhecimento facial
```bash
python src/face_realtime.py
```
- Uma janela chamada “InsightFace - Real Time” será aberta. Pressione `q` para sair.
- O console mostrará mensagens sobre a geração/uso dos embeddings e problemas de câmera.
- A cada frame, todos os rostos detectados recebem um bounding box: verde para o alvo, vermelho para desconhecidos.
- Para cada rosto analisado, é publicado `1` (alvo) ou `0` (demais) no tópico MQTT configurado na função `create_publisher()` do arquivo.

Se estiver usando outro broker/tópico, altere `BROKER`, `PORT`, `TOPIC`, `CLIENT_ID`, `USERNAME` e `PASSWORD` em `src/face_realtime.py`. O módulo `src/mqtt_publisher.py` encapsula a conexão TLS via `paho-mqtt`.

## Controlando o LED com o Raspberry Pi Pico W
1. Instale o firmware MicroPython 1.20+ na Pico W.
2. Abra `src/pico_mqtt_led.py` no Thonny (ou editor de preferência), atualize `WIFI_SSID`, `WIFI_PASSWORD` e, se necessário, as mesmas credenciais MQTT usadas no script Python.
3. Envie o arquivo para a placa (`main.py`, por exemplo) e execute.
4. Quando o reconhecimento identificar o rosto, o script receberá `1` e ligará o LED; qualquer outro payload desliga o LED (ou usa o modo `toggle` descrito no código).

## Resumo do fluxo
1. Webcam captura frames em tempo real.
2. InsightFace gera embeddings e compara com o embedding médio das fotos de referência.
3. Resultado é desenhado na tela e publicado via MQTT (`1`/`0`).
4. Um cliente MQTT (Raspberry Pi Pico W, outro microcontrolador ou mesmo um dashboard) reage ligando/desligando o LED.

## Dicas e solução de problemas
- **Latência no broker**: se o LED demorar a responder, teste primeiro o tópico com `mosquitto_sub`/`mosquitto_pub` ou outro cliente MQTT para garantir conectividade.
- **Detecção instável**: ajuste `SIMILARITY_THRESHOLD` (valores mais baixos deixam o reconhecimento mais permissivo).
- **Nova pessoa alvo**: basta trocar as fotos no diretório configurado e remover o arquivo de cache para forçar a regeneração.
- **Dependências pesadas**: `insightface` requer `onnxruntime` e `opencv`. Em máquinas sem GPU, o provedor `CPUExecutionProvider` já está configurado.
