# Monitor de Precios Agrícolas de Piura

Asistente inteligente alineado al ODS 2: Hambre Cero.

**Curso:** Herramientas de Desarrollo Profesional TIC — Sección 50876
**Docente:** Jaime José Sáenz Dedios
**Integrantes:** Carnero, Grabiel · Ruiz, Joshelyn · Benites, Franco · Ynfante, Adriel
**Universidad Tecnológica del Perú** — Piura, 2026

---

## Índice

1. [Introducción](#1-introducción)
2. [Arquitectura general del asistente](#2-arquitectura-general-del-asistente)
3. [Diseño del prompt de sistema](#3-diseño-del-prompt-de-sistema)
4. [Definición de herramientas](#4-definición-de-herramientas)
5. [Diseño del flujo de interacción](#5-diseño-del-flujo-de-interacción)
6. [Consideraciones de riesgo y ética](#6-consideraciones-de-riesgo-y-ética)
7. [Conclusiones](#7-conclusiones)
8. [Referencias](#referencias)

---

## 1. Introducción

Este documento describe la arquitectura y el diseño funcional del prototipo académico **Monitor de Precios Agrícolas de Piura**, desarrollado para el curso Herramientas de Desarrollo Profesional TIC. El sistema está alineado con el Objetivo de Desarrollo Sostenible 2 (Hambre Cero), ya que facilita el acceso y la observación de información oficial sobre el precio de los alimentos comercializados en el Mercado Modelo de Piura.

El prototipo consulta un producto dentro del conjunto de datos abiertos publicado por el Gobierno Regional Piura, compara los dos precios mayoristas válidos más recientes, calcula la variación porcentual entre ambos registros y, cuando esa variación supera un umbral configurable, genera una alerta redactada por un modelo de lenguaje local y la envía automáticamente a un canal de Telegram.

El sistema **no** predice precios, **no** explica causas de las variaciones y **no** es un asistente conversacional de propósito general. Su función se limita a informar, con trazabilidad y sobre datos oficiales, un cambio de precio calculado íntegramente en código.

---

## 2. Arquitectura general del asistente

### 2.1 Interfaz de programación utilizada como núcleo del sistema

El núcleo de inteligencia artificial es la API local de **Ollama**, consumida mediante el endpoint `/api/chat` sobre HTTP en `http://ollama:11434` dentro de la red interna de contenedores. El modelo empleado es `gemma4:e2b-it-qat`, una variante cuantizada de tamaño reducido, descargada una sola vez y conservada en el volumen persistente `ollama_models`.

La invocación se realiza desde `app/ollama_client.py`, con parámetros restrictivos:

- `temperature = 0` (elimina variabilidad estocástica)
- `num_ctx = 2048` tokens
- `num_predict = 220` tokens
- `stream` desactivado
- `format` con esquema obligatorio que fuerza una única propiedad `mensaje`

### 2.2 Justificación de la elección tecnológica

| Ventaja | Descripción |
|---|---|
| Soberanía y privacidad de datos | Toda la inferencia ocurre en la infraestructura local; ningún dato ni credencial sale del entorno. |
| Costo operativo nulo | No requiere clave de facturación ni suscripción; reproducible por cualquier integrante o el docente. |
| Compatibilidad con el esquema estándar | Usa la convención `system` / `user` / `assistant` y declaración de funciones en JSON, igual que plataformas comerciales. |
| Salida estructurada garantizada | El parámetro `format` obliga al modelo a devolver siempre un objeto con la forma esperada. |
| Determinismo verificable | Con `temperature = 0`, la misma entrada produce siempre la misma salida. |
| Separación de responsabilidades | Ollama y la app en Python corren en contenedores independientes orquestados por Docker Compose. |

### 2.3 Diagrama de flujo arquitectónico

```
Producto configurado (DEMO_PRODUCT o --producto)
        |
        v
Busqueda y validacion en el CSV oficial  [Python]
        |
        v
Seleccion de los dos precios mayoristas validos
        |
        v
Calculo local de la variacion porcentual [Python]
        |
        +---- variacion normal -----> resultado sin envio (SIN_ALERTA)
        |
        `---- variacion atipica ----> API local de Ollama
                                      Modelo gemma4:e2b-it-qat
                                              |
                                              v
                                   Validacion del mensaje generado
                                              |
                                   +----------+----------+
                                   |                     |
                              mensaje valido       mensaje invalido
                                   |                     |
                                   |              plantilla segura
                                   |                     |
                                   +----------+----------+
                                              |
                                              v
                                     API de Telegram (envio)
```

El modelo de lenguaje **no toma decisiones**. La búsqueda, la validación, el cálculo y el envío son operaciones ejecutadas por código Python determinista. El modelo cumple exclusivamente una función de redacción sobre datos ya verificados.

---

## 3. Diseño del prompt de sistema

### 3.1 Texto plano del prompt implementado

Definido en `app/prompt.py`, constante `SYSTEM_PROMPT`:

```
Eres el componente de redaccion del Monitor de Precios
Agricolas de Piura.
No eres un asistente de proposito general.

Recibiras un unico objeto JSON ya validado y calculado por la
aplicacion. Redacta solamente una alerta factual de un parrafo.

Reglas obligatorias:
1. Usa exclusivamente los valores presentes en el JSON.
2. No agregues productos, cifras, fechas, porcentajes, unidades
   ni lugares.
3. No expliques ni supongas causas como clima, escasez, oferta
   o demanda.
4. No des recomendaciones comerciales, financieras o de compra.
5. Incluye producto, dos fechas, dos precios, unidad, direccion,
   variacion, umbral y fuente.
6. Empieza exactamente con: Alerta de precio agricola - Piura.
7. Usa tono institucional, neutral y breve.
8. Devuelve un JSON con una sola propiedad llamada mensaje.
```

### 3.2 Análisis de los componentes

- **Rol:** componente de redacción, explícitamente no un asistente de propósito general.
- **Objetivo:** transformar un JSON validado en un párrafo factual; no razona ni analiza.
- **Reglas ante información ambigua:** la ambigüedad se resuelve *antes* de invocar al modelo. Si no hay coincidencias, el flujo termina en `PRODUCTO_NO_ENCONTRADO`; si hay varias, se listan y tampoco se invoca al modelo.
- **Tono institucional:** neutral, breve, con apertura textual fija y sin lenguaje de asesoría comercial (reglas 4, 6 y 7).

### 3.3 Verificación automática del cumplimiento

La función `message_is_safe` (en `app/agent.py`) audita cada respuesta: longitud máxima de 600 caracteres, apertura exacta obligatoria, ausencia de frases causales prohibidas (*debido a, causado por, probablemente, escasez, inflación, clima, demanda, oferta, recomendamos*) y presencia de los nueve datos obligatorios.

---

## 4. Definición de herramientas

Esquemas declarados en `app/tool_schemas.py` (`TOOL_SCHEMAS`), en notación de objetos JavaScript. Se definieron cuatro funciones.

### 4.1 `buscar_productos`

```json
{
  "type": "function",
  "function": {
    "name": "buscar_productos",
    "description": "Busca productos existentes en el dataset oficial de Piura.",
    "parameters": {
      "type": "object",
      "properties": {
        "consulta": { "type": "string" }
      },
      "required": ["consulta"],
      "additionalProperties": false
    }
  }
}
```

### 4.2 `obtener_precios_recientes`

```json
{
  "type": "function",
  "function": {
    "name": "obtener_precios_recientes",
    "description": "Obtiene los dos precios mayoristas validos mas recientes de un producto.",
    "parameters": {
      "type": "object",
      "properties": {
        "producto": { "type": "string" }
      },
      "required": ["producto"],
      "additionalProperties": false
    }
  }
}
```

### 4.3 `evaluar_variacion`

```json
{
  "type": "function",
  "function": {
    "name": "evaluar_variacion",
    "description": "Calcula la variacion y comprueba el umbral en codigo local.",
    "parameters": {
      "type": "object",
      "properties": {
        "producto": { "type": "string" },
        "umbral_porcentual": {
          "type": "number",
          "minimum": 0,
          "maximum": 100
        }
      },
      "required": ["producto", "umbral_porcentual"],
      "additionalProperties": false
    }
  }
}
```

Fórmula de variación porcentual:

```
V% = ((P_actual - P_anterior) / P_anterior) * 100
```

Se clasifica como atípica cuando `|V%| >= umbral`.

### 4.4 `enviar_alerta_telegram`

```json
{
  "type": "function",
  "function": {
    "name": "enviar_alerta_telegram",
    "description": "Envia una alerta validada como atipica al chat configurado.",
    "parameters": {
      "type": "object",
      "properties": {
        "analysis_id": { "type": "string" },
        "mensaje": { "type": "string" }
      },
      "required": ["analysis_id", "mensaje"],
      "additionalProperties": false
    }
  }
}
```

El token del bot y el ID del chat **no** son parámetros de esta función: se leen desde variables de entorno (`.env`, excluido del control de versiones) y nunca son visibles para el modelo.

### 4.5 Resumen comparativo

| Función | Parámetros | Ejecutor | Salida |
|---|---|---|---|
| `buscar_productos` | `consulta` (string) | Python | Lista de coincidencias |
| `obtener_precios_recientes` | `producto` (string) | Python | Dos registros válidos |
| `evaluar_variacion` | `producto` (string), `umbral_porcentual` (number, 0–100) | Python | Objeto de análisis |
| `enviar_alerta_telegram` | `analysis_id` (string), `mensaje` (string) | Python | Estado del envío |

---

## 5. Diseño del flujo de interacción

1. **Recepción de la entrada:** producto desde `DEMO_PRODUCT` o `--producto`; umbral desde `ALERT_THRESHOLD_PCT` o `--umbral`.
2. **Carga y validación de configuración** (`config.py`): verifica que el umbral esté entre 0 y 100.
3. **Ejecución de `buscar_productos`:** normaliza texto y compara contra el CSV oficial.
4. **Corte por ausencia de coincidencias:** termina en `PRODUCTO_NO_ENCONTRADO`, sin invocar a Ollama.
5. **Corte por ambigüedad:** si hay múltiples coincidencias, se listan y se detiene, sin invocar al modelo.
6. **Ejecución de `obtener_precios_recientes`:** registros ordenados por fecha descendente.
7. **Filtrado de calidad de datos:** se excluyen precios ≤ 0 y se verifica consistencia de unidad.
8. **Ejecución de `evaluar_variacion`:** aplica la fórmula, determina dirección y compara contra el umbral.
9. **Bifurcación por criticidad:** si no supera el umbral, resultado `SIN_ALERTA` sin IA ni mensajería.
10. **Construcción del payload:** JSON compacto con `producto`, `categoria`, `departamento`, `fecha_anterior`, `precio_anterior`, `fecha_actual`, `precio_actual`, `unidad`, `analysis_id`, `variacion_porcentual`, `direccion`, `umbral_porcentual`, `es_atipica`, `fuente`.
11. **Invocación del modelo:** llamada HTTP a `/api/chat` con prompt de sistema, JSON de análisis y esquema obligatorio.
12. **Extracción de la respuesta:** se lee la propiedad `mensaje`.
13. **Validación de salida:** `message_is_safe` verifica longitud, apertura, frases prohibidas y datos obligatorios.
14. **Mecanismo de respaldo:** si falla la validación o el servicio no responde, se usa la plantilla determinista `safe_message`.
15. **Ejecución de `enviar_alerta_telegram`:** envío real, o simulado si `DRY_RUN` está activo.
16. **Respuesta final:** JSON con estado (`ALERTA_PROCESADA`, `SIN_ALERTA`, `PRODUCTO_NO_ENCONTRADO`, `ERROR_CONFIGURACION`), mensaje, `analysis_id` y origen del texto.

### Caso de demostración

| Elemento | Valor obtenido |
|---|---|
| Producto | Papaya |
| Precio anterior | S/ 2.20 — 11/03/2026 |
| Precio actual | S/ 2.40 — 13/03/2026 |
| Unidad de medida | Kilogramo |
| Variación calculada | +9.09 % |
| Umbral configurado | 5.00 % |
| Clasificación | Atípica |
| Acción ejecutada | Envío de alerta a Telegram |

*(Como contraste, "Ají escabeche" produce 0.00 % de variación con sus dos registros más recientes y no genera envío.)*

---

## 6. Consideraciones de riesgo y ética

### 6.1 Riesgo 1: Generación de información falsa por el modelo de lenguaje

**Descripción:** una cifra, fecha o explicación causal inventada podría inducir decisiones económicas erróneas en comerciantes o productores.

**Mitigación (defensa en cuatro capas):**
1. Restricción del alcance del modelo — todo cálculo aritmético se hace en Python con `Decimal`.
2. Minimización del contexto — el modelo solo recibe el JSON ya verificado, nunca el dataset completo.
3. Validación posterior obligatoria — `message_is_safe` exige los nueve datos y bloquea frases causales.
4. Plantilla determinista de respaldo — `safe_message` garantiza siempre una respuesta correcta, con el origen registrado para auditoría.

### 6.2 Riesgo 2: Exposición de credenciales de acceso

**Descripción:** la filtración del token de Telegram o del chat ID permitiría a un tercero suplantar el canal oficial.

**Mitigación:**
1. Externalización de secretos en `.env`, excluido vía `.gitignore`; se distribuye solo `.env.example`.
2. Aislamiento respecto del modelo — el token y el chat ID nunca son parámetros de herramientas ni parte del prompt.
3. Modo `DRY_RUN` activo por defecto, evitando envíos accidentales.
4. Pruebas automáticas con biblioteca estándar y transportes simulados, sin credenciales reales.
5. Procedimiento de rotación mediante BotFather ante cualquier sospecha de exposición.

### 6.3 Riesgos complementarios

| Riesgo | Mitigación aplicada |
|---|---|
| Precios en cero o nulos en la fuente oficial | Filtrado previo a la selección de los dos registros recientes. |
| Consulta ajena al conjunto de datos | Toda entrada se trata como búsqueda de producto; sin coincidencia, el modelo no se ejecuta. |
| Alertas duplicadas | `analysis_id` (SHA-256) bloquea un segundo envío idéntico. |
| Interpretación del umbral como norma oficial | Se documenta explícitamente como criterio configurable del prototipo, sin valor normativo. |

### 6.4 Consideraciones éticas transversales

El prompt prohíbe atribuir causas a las variaciones (regla 3) y excluye recomendaciones comerciales o financieras (regla 4). Toda alerta incluye atribución explícita de la fuente, en cumplimiento de las condiciones de uso de los datos abiertos del Estado peruano.

---

## 7. Conclusiones

El uso de la API local de Ollama permitió construir un asistente determinista, reproducible y sin costo operativo, totalmente auditable. Mantener al modelo de lenguaje en una posición tardía y condicional del flujo fue clave para la confiabilidad del prototipo.

La definición de cuatro herramientas tipadas, con `additionalProperties: false`, estableció un contrato explícito entre la capa de datos y la de redacción. La combinación de restricciones declarativas (prompt) con validaciones imperativas (código) resultó más robusta que cualquiera de los dos mecanismos por separado, gracias a la plantilla determinista de respaldo.

La alineación con el ODS 2 se materializa en un aporte concreto: reducir la asimetría de información sobre precios de alimentos mediante difusión oportuna, trazable y no interpretativa de datos públicos oficiales.

---

## Referencias

Benites, F., Carnero, G., Ruiz, J., & Ynfante, A. (2026). *Monitor de precios agrícolas de Piura* [Software]. GitHub. https://github.com/FrancoBenites24/Monitor-de-precios-agricolas

Docker Inc. (2026). *Docker Compose documentation*. https://docs.docker.com/compose/

Gobierno Regional Piura. (2026). *Precios mayorista y minorista del Mercado Modelo de Piura* [Conjunto de datos]. Plataforma Nacional de Datos Abiertos del Perú. https://www.datosabiertos.gob.pe/dataset/precios-mayorista-y-minorista-del-mercado-modelo-de-piuragobierno-regional-piura-grp-0

Ollama. (2026). *Ollama API documentation*. https://github.com/ollama/ollama/blob/main/docs/api.md

Organización de las Naciones Unidas. (2015). *Objetivo de Desarrollo Sostenible 2: Hambre cero*. https://www.un.org/sustainabledevelopment/es/hunger/

Telegram. (2026). *Telegram Bot API*. https://core.telegram.org/bots/api