import os
import unittest
from unittest.mock import patch
from uuid import UUID

import httpx

from app.config import Settings
from app.integrations.decoction import upload_to_simulation
from app.prescriptions.models import SimulationUploadRequest


class DecoctionProxyTests(unittest.TestCase):
    def test_proxy_is_opt_in_and_loaded_from_server_environment(self):
        self.assertEqual(Settings(rag_enabled=False).decoction_proxy_url, "")
        with patch.dict(os.environ, {"DECOCTION_PROXY_URL": " http://127.0.0.1:9876/ ", "RAG_ENABLED": "true"}):
            settings = Settings.from_env()
        self.assertEqual(settings.decoction_proxy_url, "http://127.0.0.1:9876")
        self.assertNotIn("9876", repr(settings))

    def test_invalid_proxy_configuration_is_rejected_without_echoing_it(self):
        for proxy in ("socks5://127.0.0.1:9876", "http://", "http://private:secret@127.0.0.1:9876",
                      "http://127.0.0.1:9876/path", "http://127.0.0.1:9876?secret=value",
                      "http://127.0.0.1:9876#secret", "http://127.0.0.1:invalid"):
            with self.subTest(proxy=proxy):
                with self.assertRaises(ValueError) as caught:
                    Settings(rag_enabled=False, decoction_proxy_url=proxy)
                self.assertNotIn("secret", str(caught.exception))

    @patch("app.integrations.decoction.httpx.post")
    def test_upload_uses_explicit_proxy_without_enabling_environment_proxy(self, post):
        identifier = UUID("12345678-1234-4234-8234-1234567890ab")
        external_no = "BENCAO-" + identifier.hex.upper()
        request = SimulationUploadRequest(upload_id=identifier, doses=3, medicines=[
            {"name": "测试饮片", "dose": "9", "unit": "g", "dose_scope": "per_dose", "method": "常规"}])
        post.return_value = httpx.Response(201, json={"external_no": external_no, "status": "pending_review"})
        result = upload_to_simulation(Settings(rag_enabled=False, decoction_proxy_url="http://127.0.0.1:9876"), request)
        self.assertEqual(result["external_no"], external_no)
        self.assertEqual(post.call_args.kwargs["proxy"], "http://127.0.0.1:9876")
        self.assertFalse(post.call_args.kwargs["trust_env"])
