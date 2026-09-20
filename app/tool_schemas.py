TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_productos",
            "description": "Busca productos existentes en el dataset oficial de Piura.",
            "parameters": {
                "type": "object",
                "properties": {"consulta": {"type": "string"}},
                "required": ["consulta"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_precios_recientes",
            "description": "Obtiene los dos precios mayoristas validos mas recientes de un producto.",
            "parameters": {
                "type": "object",
                "properties": {"producto": {"type": "string"}},
                "required": ["producto"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluar_variacion",
            "description": "Calcula la variacion y comprueba el umbral en codigo local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "producto": {"type": "string"},
                    "umbral_porcentual": {"type": "number", "minimum": 0, "maximum": 100},
                },
                "required": ["producto", "umbral_porcentual"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_alerta_telegram",
            "description": "Envia una alerta validada como atipica al chat configurado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_id": {"type": "string"},
                    "mensaje": {"type": "string"},
                },
                "required": ["analysis_id", "mensaje"],
                "additionalProperties": False,
            },
        },
    },
]
