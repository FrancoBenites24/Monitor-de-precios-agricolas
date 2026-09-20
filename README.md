# Monitor de Precios Agrícolas

Proyecto académico orientado al desarrollo de un agente de inteligencia artificial capaz de analizar información oficial sobre precios agrícolas en el Perú y generar alertas cuando se detecten variaciones relevantes.

El proyecto se encuentra relacionado con el **ODS 2: Hambre Cero**.

---

## Objetivo del proyecto

Desarrollar una aplicación sencilla que permita consultar el precio de un producto agrícola utilizando información oficial de la Plataforma Nacional de Datos Abiertos del Perú.

El sistema deberá:

1. Leer información oficial de precios agrícolas.
2. Permitir consultar un producto.
3. Obtener sus precios registrados.
4. Comparar el precio actual con un precio anterior.
5. Calcular la variación porcentual.
6. Detectar si existe una variación significativa.
7. Utilizar inteligencia artificial para generar una alerta.
8. Enviar la alerta automáticamente mediante una plataforma de mensajería.

> El procesamiento y filtrado del archivo de datos debe realizarse mediante código.  
> El archivo completo no será enviado al modelo de inteligencia artificial.

---

# Alcance inicial

El proyecto será desarrollado como un **MVP (Producto Mínimo Viable)**.

## El sistema sí hará

- Trabajará con datos oficiales del Perú.
- Leerá archivos de precios agrícolas.
- Permitirá buscar un producto.
- Obtendrá registros de precios.
- Comparará precios.
- Calculará la variación porcentual.
- Detectará una variación significativa mediante un umbral definido.
- Generará un mensaje mediante inteligencia artificial.
- Enviará una alerta automáticamente.

## El sistema no incluirá inicialmente

- Sistema de usuarios.
- Login.
- Base de datos propia.
- Aplicación móvil.
- Dashboard avanzado.
- Predicción futura de precios.
- Machine Learning.
- WebSockets.
- Precios actualizados cada segundo.
- Scraping continuo.
- Sistema de pagos.

Estas características podrían incorporarse posteriormente, pero no forman parte del alcance inicial.

---

# Fuente de datos

Los datos utilizados deberán provenir de la:

**Plataforma Nacional de Datos Abiertos del Perú**

Dataset inicialmente considerado:

### Precios mayoristas y minoristas del Mercado Modelo de Piura

Fuente:

https://www.datosabiertos.gob.pe/

El equipo deberá verificar el dataset definitivo y documentar:

- nombre del dataset;
- institución responsable;
- URL oficial;
- formato disponible;
- fecha de actualización;
- columnas existentes;
- productos disponibles.

---

# Flujo esperado

```text
Usuario
   │
   ▼
Ingresa producto
   │
   ▼
Procesamiento del dataset
   │
   ▼
Obtención de precios
   │
   ▼
Cálculo de variación
   │
   ▼
¿Existe variación significativa?
   │
   ├── NO → mostrar resultado
   │
   └── SÍ
        │
        ▼
   Agente de IA
        │
        ▼
 Generación de alerta
        │
        ▼
 Plataforma de mensajería
