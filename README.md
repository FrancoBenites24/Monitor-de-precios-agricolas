# Monitor de precios agricolas de Piura

Bot conversacional de Telegram para consultar precios mayoristas del Mercado Modelo de Piura. Usa el dataset oficial, calcula todos los resultados en Python y emplea `gemma4:e2b-it-qat` mediante Ollama solamente para clasificar preguntas ambiguas y redactar alertas.

El bot esta limitado al dataset agricola. No responde preguntas generales, no predice precios y no inventa causas para una variacion.

## Lo unico que debe configurar el compañero

1. Crear el bot con `@BotFather` usando `/newbot`.
2. Copiar `.env.example` como `.env`.
3. Pegar el token:

```dotenv
TELEGRAM_BOT_TOKEN=token_entregado_por_BotFather
```

No necesita `chat_id`, dominio, webhook ni una clave de OpenAI.

## Desplegar

En Windows puede hacer doble clic en `INICIAR.bat`. Tambien puede ejecutar:

```powershell
docker compose up --build
```

Docker inicia Ollama, descarga `gemma4:e2b-it-qat`, registra el menu de comandos de Telegram y mantiene el bot escuchando mediante long polling. La primera descarga del modelo es de aproximadamente 4.3 GB y se conserva en el volumen `ollama_models`.

Despues del despliegue, el usuario abre el bot en Telegram, presiona **Iniciar** y conversa en ese mismo chat.

## Consultas disponibles

El usuario puede escribir preguntas sencillas:

```text
¿Cuanto cuesta la papaya?
¿La papaya subio o bajo?
Muestrame el historial del limon
Historial de papaya en los ultimos 12 meses
Avisame si la papaya cambia mas de 5%
¿Que productos tienes?
```

Tambien dispone de comandos exactos:

```text
/precio Papaya
/variacion Papaya
/historial Papaya 12
/alerta Papaya 5
/productos
/ayuda
```

`/historial` acepta entre 1 y 60 meses. Si no se indica la cantidad, resume todo el periodo disponible del producto.

## Respuestas del bot

- **Precio:** ultimo precio mayorista, unidad y fecha.
- **Variacion:** comparacion de los dos registros validos mas recientes.
- **Historial:** periodo, cantidad de registros, promedio, minimo, maximo, variacion y promedios por ano.
- **Alerta:** compara la variacion con el umbral. Gemma redacta el mensaje solo cuando el cambio es atipico.
- **Productos:** lista de los 51 productos disponibles.

Si una consulta coincide con varios productos, el bot muestra opciones. Por ejemplo, `precio de papa` solicita elegir entre `Papa amarilla` y `Papa canchan`.

## Limites de la IA

La entrada pasa por estas protecciones:

1. Los comandos y preguntas frecuentes se interpretan directamente en Python.
2. Gemma solo clasifica una pregunta cuando la intencion no es evidente.
3. La clasificacion solo admite intenciones conocidas y productos del CSV.
4. Una consulta ajena devuelve un mensaje fijo con `/ayuda`.
5. Fechas, precios, promedios y variaciones se calculan en Python.
6. El CSV completo y el token de Telegram nunca se envian al modelo.
7. Una alerta generada por Gemma se valida; si agrega datos o causas, se reemplaza por una plantilla segura.

## Pruebas

No requieren Ollama ni Telegram:

```powershell
python -m unittest discover -s tests -v
```

## Estructura

```text
app/
  bot_main.py          inicio del bot
  bot_runner.py        recepcion por long polling
  chatbot.py           respuestas del chat
  intent.py            comandos y preguntas naturales
  dataset.py           lectura y consulta del CSV
  analysis.py          calculos deterministas
  ollama_client.py     clasificacion y redaccion local
  telegram_client.py   Telegram Bot API
  tool_schemas.py      herramientas JSON
data/
  mimercado_dataset.csv
tests/
Dockerfile
docker-compose.yml
INFORME_TECNICO.md
```

## Fuente

Gobierno Regional Piura. Precios mayorista y minorista del Mercado Modelo de Piura:

https://www.datosabiertos.gob.pe/dataset/precios-mayorista-y-minorista-del-mercado-modelo-de-piuragobierno-regional-piura-grp-0
