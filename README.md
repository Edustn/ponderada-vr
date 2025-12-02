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

## Protótipo VR em A-Frame
A pasta `web/` contém o primeiro rascunho da cena VR/AR que será exibida no Meta Quest. Ela foi criada em cima do A-Frame (WebXR) e já implementa:
- Spawn de quatro balões animados, cada um com texto associado.
- Controle por laser (`laser-controls`) nos dois handsets — basta mirar e apertar o gatilho para estourar.
- Sequenciamento das mensagens e, no fim, um coração 3D simples construído com primitivas.
- Função global `window.startBalloonRound()` para reiniciar o jogo quando o backend detectar o rosto.
- Um cenário “storybook” com roda-gigante, casinhas, árvores e sol estilizado construídos com primitivas A-Frame.

### Como testar localmente
```bash
cd web
python -m http.server 5500
```
1. Abra `http://<ip-da-sua-máquina>:5500` no navegador do Quest (ou no desktop para depurar).
2. Clique em “Enter VR”. Você verá os controladores virtuais com lasers verdes.
3. Mire nos balões e aperte o gatilho; as mensagens vão mudando e, após o último balão, aparece o coração.

#### Servindo com Caddy via Docker
Se preferir subir a cena com o `Caddyfile` existente, entre primeiro na pasta `web/` e então execute:
```bash
cd web
docker run -d --rm \
  --name caddy-server \
  -p 8080:80 \
  -p 4430:443 \
  -v $(pwd)/Caddyfile:/etc/caddy/Caddyfile \
  -v $(pwd):/usr/share/caddy \
  -v caddy_data:/data \
  -v caddy_config:/config \
  caddy:latest
```
Isso inicia o Caddy em segundo plano usando o `Caddyfile` da pasta `web/`. Acesse `http://localhost:8080` (ou `https://0.0.0.0:4430/index.html`) e finalize com `docker stop caddy-server` quando terminar.

### Integração com o reconhecimento facial
- O `face_realtime.py` continua como fonte da verdade publicando no MQTT.
- Um pequeno backend (Python/Node) pode assinar o mesmo tópico e, quando receber `1`, disparar `startBalloonRound()` via WebSocket para a página aberta no Quest.
- Assim que o evento chegar via WebSocket, basta chamar `window.startBalloonRound()` para exibir novamente os balões e mensagens.

Esse fluxo mantém o reconhecimento desacoplado e permite evoluir o front com animações, assets glTF ou mesmo AR pass-through sem tocar no pipeline de InsightFace/MQTT.

### Assets da cena
- Se quiser complementar com texturas ou modelos externos, coloque-os em `web/assets/` e referencie na tag `<a-assets>`.

## Dicas e solução de problemas
- **Latência no broker**: se o LED demorar a responder, teste primeiro o tópico com `mosquitto_sub`/`mosquitto_pub` ou outro cliente MQTT para garantir conectividade.
- **Detecção instável**: ajuste `SIMILARITY_THRESHOLD` (valores mais baixos deixam o reconhecimento mais permissivo).
- **Nova pessoa alvo**: basta trocar as fotos no diretório configurado e remover o arquivo de cache para forçar a regeneração.
- **Dependências pesadas**: `insightface` requer `onnxruntime` e `opencv`. Em máquinas sem GPU, o provedor `CPUExecutionProvider` já está configurado.
