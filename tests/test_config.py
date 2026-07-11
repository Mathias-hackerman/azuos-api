import importlib
import os
import unittest


class ConfigTests(unittest.TestCase):
    def test_agent_url_uses_port_8000(self):
        os.environ["AI_AGENT_URL"] = "https://example.onrender.com:10000"
        import app.config as config_module

        importlib.reload(config_module)

        self.assertEqual(config_module.Config.AI_AGENT_URL, "https://example.onrender.com:8000")


if __name__ == "__main__":
    unittest.main()
