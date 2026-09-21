# Propuesta tecnica - Monitor de precios agricolas

## Alcance y objetivo

El sistema es un bot conversacional de Telegram para consultar precios mayoristas del Mercado Modelo de Piura. Se alinea con el ODS 2: Hambre cero al facilitar el acceso a informacion oficial sobre alimentos. No predice precios, no recomienda compras o ventas y no explica causas que el dataset no contiene.

La fuente es el dataset publicado por el Gobierno Regional Piura en la Plataforma Nacional de Datos Abiertos del Peru. La aplicacion procesa localmente `PRECIO_MAYORISTA`; nunca envia el CSV completo al modelo.

## 1. Arquitectura general del asistente

```text
Usuario en Telegram
        |
        v
Telegram Bot API (long polling)
        |
        v
Interprete de comandos e intenciones
        |
        +--> precio / variacion / historial / productos
        |           |
        |           `--> calculo local sobre el CSV
        |
        `--> consulta ambigua --> Ollama + Gemma 4 E2B
                                      |
                                      `--> intencion JSON validada
        |
        v
Respuesta en el mismo chat
```

La interfaz principal es Telegram y la API local de Ollama es el nucleo de IA. `gemma4:e2b-it-qat` se usa para clasificar preguntas que no coinciden con reglas directas y para redactar una alerta atipica. Python conserva el control del flujo y de todos los calculos.

Se eligio long polling porque no necesita dominio, certificado ni webhook. Docker Compose ejecuta la aplicacion y Ollama en servicios separados, descarga el modelo automaticamente y lo conserva en un volumen.

## 2. Diseño del prompt de sistema

El prompt de alertas esta en `app/prompt.py`. Define al modelo como redactor del Monitor de Precios Agricolas de Piura y le exige:

- usar exclusivamente el JSON calculado;
- no agregar productos, cifras, fechas, unidades o lugares;
- no suponer causas como clima, escasez, oferta o demanda;
- no dar recomendaciones comerciales;
- mantener un tono institucional y breve;
- responder en un objeto JSON con un solo mensaje.

La clasificacion de preguntas tiene otro contrato cerrado: solo puede devolver `PRECIO`, `VARIACION`, `HISTORIAL`, `PRODUCTOS`, `ALERTA`, `AYUDA` o `FUERA_DE_ALCANCE`, junto con un producto de la lista oficial. El texto generado durante la clasificacion nunca se muestra al usuario.

## 3. Definicion de herramientas

Los cinco esquemas JSON se encuentran en `app/tool_schemas.py`:

1. `buscar_productos(consulta)`: busca nombres validos en el dataset.
2. `obtener_precios_recientes(producto)`: selecciona los dos registros mayoristas positivos mas recientes.
3. `evaluar_variacion(producto, umbral_porcentual)`: calcula el porcentaje y determina si es atipico.
4. `consultar_historial(producto, meses)`: resume entre 1 y 60 meses o todo el periodo disponible.
5. `enviar_alerta_telegram(analysis_id, mensaje)`: envia una alerta previamente validada.

Cada esquema declara nombre, descripcion, parametros obligatorios y `additionalProperties=false`. El token de Telegram se obtiene del entorno y no forma parte de las herramientas del modelo.

## 4. Diseño del flujo de interaccion

1. El usuario abre el bot y escribe un comando o una pregunta natural.
2. Python detecta primero comandos y expresiones conocidas.
3. Si la intencion no es clara, Gemma devuelve solamente una clasificacion JSON.
4. El sistema valida que el producto exista en el CSV.
5. Si existen varias coincidencias, el bot muestra opciones y pide el nombre completo.
6. Si la pregunta es ajena al dataset, responde con un texto fijo de ayuda.
7. Para `PRECIO`, obtiene el registro mayorista valido mas reciente.
8. Para `VARIACION`, compara los dos registros recientes y calcula el porcentaje.
9. Para `HISTORIAL`, calcula promedio, minimo, maximo, variacion y promedios anuales.
10. Para `ALERTA`, aplica el umbral y solicita a Gemma una redaccion solo si el cambio es atipico.
11. La alerta se valida; si contiene datos no permitidos, se reemplaza por una plantilla segura.
12. Telegram devuelve el resultado en el mismo chat del usuario.

Comandos: `/precio`, `/variacion`, `/historial`, `/alerta`, `/productos` y `/ayuda`.

## 5. Consideraciones de riesgo y etica

| Riesgo | Mitigacion aplicada |
|---|---|
| Precios iguales a cero | Se excluyen antes de seleccionar o resumir registros. |
| Respuesta ajena al dataset | Las intenciones y los productos usan listas cerradas. |
| Cifras o causas inventadas | Los calculos se hacen en Python y la alerta generada se valida. |
| Exposicion de credenciales | El token permanece en `.env`, fuera de Git y del prompt. |
| Consulta ambigua | El bot muestra las coincidencias y solicita el nombre completo. |
| Umbral interpretado como norma oficial | Se documenta como criterio configurable del prototipo. |
| Historial confundido con precio al productor | Cada respuesta lo identifica como precio mayorista del Mercado Modelo de Piura. |

## Utilidad para el agricultor

Desde su celular, el usuario puede consultar el ultimo precio publicado, observar la variacion reciente, revisar estadisticas historicas y evaluar cambios atipicos. La informacion funciona como referencia mayorista para seguimiento y negociacion, no como precio garantizado en chacra.

## Fuente oficial

https://www.datosabiertos.gob.pe/dataset/precios-mayorista-y-minorista-del-mercado-modelo-de-piuragobierno-regional-piura-grp-0
