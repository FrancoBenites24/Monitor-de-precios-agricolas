# Monitor de precios agricolas de Piura

Prototipo academico alineado con el ODS 2: Hambre cero. Consulta un producto del dataset oficial del Mercado Modelo de Piura, compara sus dos precios mayoristas validos mas recientes y envia una alerta a Telegram cuando la variacion supera el umbral configurado.

## Que esta listo

- Dataset oficial incluido sin modificaciones.
- Lectura, validacion y filtrado del CSV en Python.
- Calculo local de la variacion porcentual.
- Modelo local `gemma4:e2b-it-qat` servido por Ollama.
- Redaccion limitada exclusivamente a los datos del analisis.
- Integracion saliente con Telegram.
- Docker Compose con descarga automatica y persistente del modelo.
- Pruebas automaticas sin conexiones externas.

La aplicacion no es un chatbot general. La entrada solo se usa para buscar un producto en el CSV. Si el producto no existe, Ollama no recibe ninguna solicitud.

## Lo unico que debe configurar el compañero

Abrir `.env` y completar:

```dotenv
TELEGRAM_BOT_TOKEN=token_entregado_por_BotFather
TELEGRAM_CHAT_ID=identificador_del_chat
```

No se debe cambiar ningun archivo Python.

Para obtener el chat ID:

1. Crear el bot con BotFather y copiar el token.
2. Abrir el chat con el bot y enviar `/start`.
3. Consultar `https://api.telegram.org/bot<TOKEN>/getUpdates`.
4. Copiar el valor numerico de `message.chat.id`.

## Iniciar todo

Desde esta carpeta:

```powershell
docker compose up --build
```

En Windows tambien puede hacerse doble clic en `INICIAR.bat`. El archivo comprueba primero que las dos credenciales de Telegram esten completas.

La primera ejecucion descarga `gemma4:e2b-it-qat`, de aproximadamente 4.3 GB. El modelo se conserva en el volumen `ollama_models`, por lo que no se vuelve a descargar al reconstruir la aplicacion.

Docker Compose realiza automaticamente este flujo:

1. Inicia Ollama.
2. Descarga o verifica el modelo.
3. Inicia la aplicacion.
4. Consulta `Papaya` con un umbral de 5%.
5. Genera la alerta con Gemma.
6. La valida y la envia a Telegram.

## Caso de demostracion

La configuracion predeterminada usa datos reales:

```text
Producto: Papaya
Precio anterior: 2.20 el 11/03/2026
Precio actual: 2.40 el 13/03/2026
Variacion: +9.09%
Umbral: 5.00%
Resultado: alerta atipica
```

Para cambiar de producto, editar `DEMO_PRODUCT` en `.env`. Por ejemplo, `Aji escabeche` produce 0.00% con los dos registros mas recientes y no envia alerta.

## Seguridad de la respuesta

El programa aplica cuatro controles:

1. Solo acepta productos que existan en el CSV.
2. Calcula fechas, precios y porcentajes en Python.
3. Envia a Gemma un solo JSON pequeno, nunca el CSV completo.
4. Rechaza la respuesta del modelo si falta un dato obligatorio, agrega una causa o no usa el formato esperado. En ese caso utiliza una plantilla segura con los mismos datos.

El token y el chat de Telegram nunca se entregan al modelo.

## Pruebas

Las pruebas usan la biblioteca estandar de Python y no necesitan Ollama, Docker ni Telegram:

```powershell
python -m unittest discover -s tests -v
```

## Estructura

```text
app/
  agent.py            flujo restringido y controles de salida
  analysis.py         formula de variacion
  config.py           variables de entorno
  dataset.py          lectura y busqueda del CSV
  ollama_client.py    llamada local al modelo
  prompt.py           prompt de sistema
  telegram_client.py  envio saliente
  tool_schemas.py     cuatro herramientas JSON
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
