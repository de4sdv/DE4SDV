import unittest

from tools import generate_covesa_vss_sysmlv2 as generator


class CovesaVssGeneratorTests(unittest.TestCase):
    def test_allowed_values_generate_enum_def_with_sanitized_literals(self):
        lines = generator.enum_definition_block(
            "Vehicle.ADAS.ActiveAutonomyLevel",
            ["SAE_0", "SAE 2 DISENGAGING", "3D-mode", "off/on"],
        )

        self.assertEqual(
            lines,
            [
                "  enum def Vehicle_ADAS_ActiveAutonomyLevel_AllowedValue {",
                "    SAE_0;",
                "    SAE_2_DISENGAGING;",
                "    V_3D_mode;",
                "    off_on;",
                "  }",
            ],
        )

    def test_sysml_type_uses_generated_enum_for_allowed_values(self):
        value = {"datatype": "string", "allowed": ["FORWARD", "REVERSE"]}

        self.assertEqual(
            generator.sysml_type("Vehicle.Direction", value),
            "Vehicle_Direction_AllowedValue",
        )

    def test_sysml_type_falls_back_to_scalar_without_allowed_values(self):
        value = {"datatype": "float"}

        self.assertEqual(generator.sysml_type("Vehicle.Speed", value), "Real")


if __name__ == "__main__":
    unittest.main()
