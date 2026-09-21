import unittest

from app.tool_schemas import TOOL_SCHEMAS


class ToolSchemaTests(unittest.TestCase):
    def test_five_closed_function_schemas_exist(self) -> None:
        self.assertEqual(len(TOOL_SCHEMAS), 5)
        names = set()
        for schema in TOOL_SCHEMAS:
            self.assertEqual(schema["type"], "function")
            function = schema["function"]
            names.add(function["name"])
            self.assertTrue(function["description"])
            self.assertFalse(function["parameters"]["additionalProperties"])
            self.assertTrue(function["parameters"]["required"])
        self.assertEqual(
            names,
            {
                "buscar_productos",
                "obtener_precios_recientes",
                "evaluar_variacion",
                "consultar_historial",
                "enviar_alerta_telegram",
            },
        )


if __name__ == "__main__":
    unittest.main()
