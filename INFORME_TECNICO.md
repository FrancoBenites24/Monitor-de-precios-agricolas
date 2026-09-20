# Propuesta tecnica - Monitor de precios agricolas

## Alcance y objetivo

El sistema apoya la observacion de variaciones recientes de precios agricolas del Mercado Modelo de Piura. Se alinea con el ODS 2: Hambre cero al facilitar la consulta de informacion oficial vinculada con alimentos. No predice precios ni explica sus causas.

La fuente es el dataset de precios mayoristas y minoristas publicado por el Gobierno Regional Piura en la Plataforma Nacional de Datos Abiertos del Peru. El prototipo usa `PRECIO_MAYORISTA`, procesa el CSV internamente y no entrega el archivo completo al modelo.

## 1. Arquitectura general del asistente

```text
Producto configurado
        |
        v
Busqueda y validacion del CSV
        |
        v
Calculo local de la variacion
        |
        +---- variacion normal ----> resultado sin envio
        |
        `---- variacion atipica ---> Ollama + Gemma 4 E2B
                                           |
                                           v
                                  validacion del mensaje
                                           |
                                           v
                                         Telegram
```

La interfaz central es la API local de Ollama. El modelo seleccionado es `gemma4:e2b-it-qat` porque la tarea solo requiere redactar un mensaje corto a partir de datos ya calculados. La aplicacion usa un flujo cerrado en Python para evitar que el modelo responda preguntas generales o modifique reglas de negocio.

Ollama y la aplicacion se ejecutan en servicios separados de Docker Compose. El modelo se guarda en un volumen persistente. Esta division permite actualizar el codigo sin volver a descargar los pesos y mantiene la aplicacion Python sin dependencias externas.

## 2. Diseño del prompt de sistema

El prompt se encuentra en `app/prompt.py` y define:

- rol: redactor del Monitor de Precios Agricolas de Piura;
- objetivo: redactar una alerta factual de un solo parrafo;
- limites: utilizar exclusivamente el JSON calculado;
- informacion ambigua: el modelo no participa hasta que el producto sea unico y los datos sean validos;
- prohibiciones: inventar cifras, fechas, unidades, causas o recomendaciones;
- tono: institucional, neutral y breve;
- formato: JSON con una sola propiedad `mensaje`.

El modelo nunca recibe el texto como una conversacion abierta. La aplicacion le entrega solamente el contrato del analisis cuando `es_atipica=true`.

## 3. Definicion de herramientas

Los esquemas completos estan en `app/tool_schemas.py`. Se definieron cuatro funciones en notacion de objetos JavaScript:

1. `buscar_productos(consulta)`: limita la entrada a nombres presentes en el dataset.
2. `obtener_precios_recientes(producto)`: selecciona los dos precios mayoristas positivos mas recientes.
3. `evaluar_variacion(producto, umbral_porcentual)`: calcula el porcentaje y determina si es atipico.
4. `enviar_alerta_telegram(analysis_id, mensaje)`: envia exclusivamente un analisis validado.

Cada esquema declara nombre, descripcion, parametros obligatorios y `additionalProperties=false`. El token y el chat de Telegram no son parametros de una herramienta; se leen desde el entorno y nunca se muestran al modelo.

## 4. Diseño del flujo de interaccion

1. La aplicacion recibe el nombre configurado en `DEMO_PRODUCT` o mediante `--producto`.
2. Ejecuta `buscar_productos` sin llamar al modelo.
3. Si no existe coincidencia, termina con `PRODUCTO_NO_ENCONTRADO`.
4. Si existen varias coincidencias, devuelve sus nombres y no llama al modelo.
5. Para una coincidencia unica, ejecuta `obtener_precios_recientes`.
6. Excluye precios mayoristas menores o iguales a cero y verifica la unidad.
7. Ejecuta `evaluar_variacion` con la formula `((actual - anterior) / anterior) * 100`.
8. Si la variacion no supera el umbral, informa el resultado sin usar IA ni Telegram.
9. Si es atipica, envia a Gemma solamente el JSON del analisis.
10. Valida que la respuesta contenga todos los datos y no incluya causas o recomendaciones.
11. Si la respuesta no es valida, la reemplaza por una plantilla segura y registra el origen.
12. Ejecuta `enviar_alerta_telegram` y muestra el estado final.

La automatizacion visible exigida es la llegada del mensaje al chat de Telegram durante la exposicion.

## 5. Consideraciones de riesgo y etica

| Riesgo | Mitigacion aplicada |
|---|---|
| Precios iguales a cero en la fuente | Se excluyen antes de seleccionar los dos registros recientes. |
| Respuesta inventada por el modelo | Se valida cada dato obligatorio y se bloquean explicaciones causales. |
| Consulta ajena al dataset | Se trata como busqueda de producto; si no coincide, la IA no se ejecuta. |
| Exposicion de credenciales | Token y chat permanecen en `.env`, fuera de Git y fuera del prompt. |
| Alertas duplicadas | Se conserva el identificador del analisis durante la ejecucion y se omite un segundo envio. |
| Interpretacion del umbral como norma oficial | El README lo identifica como un criterio configurable del prototipo. |

## Evidencia para la demostracion

Con `Papaya` y un umbral de 5% el dataset devuelve:

- 11/03/2026: 2.20 por KILOGRAMO;
- 13/03/2026: 2.40 por KILOGRAMO;
- variacion: +9.09%;
- clasificacion: atipica.

Esta informacion se obtiene durante la ejecucion; no esta fijada como resultado dentro del codigo.

## Fuente oficial

https://www.datosabiertos.gob.pe/dataset/precios-mayorista-y-minorista-del-mercado-modelo-de-piuragobierno-regional-piura-grp-0
