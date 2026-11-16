import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from app.config import Settings
from app.main import create_app
from app.prescriptions.agent import PrescriptionAgent
from app.prescriptions.files import read_upload
from app.prescriptions.vision import parse_multimodal
from app.security import hash_password
from RAG.llm import request_json


def sample_result(**changes):
    result = {"intent": {"kind": "prescription_check", "explanation": "一份演示处方", "multiple_prescriptions": False},
              "transcription": "大枣 3枚 同煎\n生姜 3片 同煎",
              "prescription": {"medicines": [
                  {"name": "大枣", "dose": "3", "unit": "枚", "source": "大枣 3枚 同煎"},
                  {"name": "生姜", "dose": "3", "unit": "片", "source": "生姜 3片 同煎"},
              ]}}
    result.update(changes)
    return result


def sample_image():
    stream = BytesIO()
    Image.new("RGB", (180, 100), "white").save(stream, "PNG")
    return stream.getvalue()


class MultimodalTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(rag_enabled=False, deepseek_api_key="unit-test")

    def test_image_path_uses_one_model_call_and_returns_no_encoded_images(self):
        with patch("app.prescriptions.vision.request_json", return_value=json.dumps(sample_result())) as send, patch(
            "app.prescriptions.agent.classify", side_effect=AssertionError("image must not call text classifier"),
        ):
            result = PrescriptionAgent(self.settings).run({"phase": "prepare", "content": sample_image(),
                       "filename": "rx.png", "instruction": "提取", "dose_scope": "per_dose"})
        send.assert_called_once()
        self.assertEqual(len(send.call_args.kwargs["image_urls"]), 1)
        self.assertEqual(result["steps"], ["read_upload", "parse_multimodal", "confirm_data"])
        self.assertEqual(result["status"], "needs_confirmation")
        self.assertEqual(result["source"]["method"], "image_vision")
        self.assertEqual(result["source"]["verification"], "model_transcription")
        self.assertNotIn("images", result["source"])
        self.assertNotIn("base64,", json.dumps(result))
        self.assertEqual([(m["dose"], m["unit"]) for m in result["prescription"]["medicines"]], [("3", "枚"), ("3", "片")])
        self.assertTrue(all(m["dose_scope"] == "per_dose" for m in result["prescription"]["medicines"]))

    def test_non_prescription_and_multiple_versions_never_enter_confirmation(self):
        for intent in [{"kind": "not_prescription", "explanation": "药材介绍", "multiple_prescriptions": False},
                       {"kind": "prescription_check", "explanation": "多个版本", "multiple_prescriptions": True}]:
            with self.subTest(intent=intent), patch("app.prescriptions.vision.request_json", return_value=json.dumps(sample_result(intent=intent))):
                result = PrescriptionAgent(self.settings).run({"phase": "prepare", "content": sample_image(), "filename": "rx.png"})
            self.assertEqual(result["status"], "needs_clarification")
            self.assertIsNone(result["prescription"])

    def test_malformed_or_inconsistent_result_is_rejected_without_echoing_it(self):
        mismatched = sample_result()
        mismatched["prescription"]["medicines"][0]["dose"] = "99"
        for payload in ["not-json", json.dumps(sample_result(prescription=None)), json.dumps(mismatched),
                        json.dumps({**sample_result(), "unexpected_private_data": "must-not-echo"})]:
            with self.subTest(payload=payload), patch("app.prescriptions.vision.request_json", return_value=payload):
                with self.assertRaises(HTTPException) as error:
                    parse_multimodal(self.settings, read_upload(sample_image(), "rx.png"), "提取")
            self.assertEqual(error.exception.status_code, 502)
            self.assertNotIn("must-not-echo", error.exception.detail)

    def test_vision_failure_does_not_fall_back_to_text_or_local_ocr(self):
        with patch("app.prescriptions.vision.request_json", side_effect=HTTPException(504, "AI 服务响应超时")) as send:
            with self.assertRaises(HTTPException) as error:
                PrescriptionAgent(self.settings).run({"phase": "prepare", "content": sample_image(), "filename": "rx.png"})
        self.assertEqual(error.exception.status_code, 504)
        send.assert_called_once()

    def test_unconfigured_vision_never_sends_a_request(self):
        with patch("app.prescriptions.vision.request_json") as send:
            with self.assertRaises(HTTPException) as error:
                PrescriptionAgent(Settings(rag_enabled=False)).run({"phase": "prepare", "content": sample_image(), "filename": "rx.png"})
        self.assertEqual(error.exception.status_code, 503)
        send.assert_not_called()

    def test_image_api_auth_csrf_and_manual_confirmation_remain_required(self):
        with TemporaryDirectory() as directory:
            app = create_app(Settings(rag_enabled=False, database=Path(directory) / "test.db", deepseek_api_key="unit-test"))
            with TestClient(app) as client, patch("app.prescriptions.vision.request_json", return_value=json.dumps(sample_result())) as send:
                upload = {"file": ("rx.png", sample_image(), "image/png")}
                self.assertEqual(client.post("/api/prescriptions/prepare", files=upload).status_code, 403)
                self.assertEqual(client.post("/api/prescriptions/prepare", files=upload, headers={"X-CSRF-Protection": "1"}).status_code, 401)
                send.assert_not_called()
                with app.state.database.connect() as db:
                    db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                               ("qa_viewer", "虚构测试", hash_password("unit-test-secret"), "viewer", 1))
                client.headers["X-CSRF-Protection"] = "1"
                self.assertEqual(client.post("/api/auth/login", json={"username": "qa_viewer", "password": "unit-test-secret"}).status_code, 200)
                result = client.post("/api/prescriptions/prepare", files=upload)
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(client.post("/api/prescriptions/check", json={"prescription": result.json()["prescription"], "confirmed": False}).status_code, 422)
                send.assert_called_once()


class VisionTransportTests(unittest.TestCase):
    def test_image_is_sent_as_a_visual_content_block_not_text(self):
        response = httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})
        with patch("RAG.llm.httpx.Client") as client:
            post = client.return_value.__enter__.return_value.post
            post.return_value = response
            self.assertEqual(request_json(Settings(deepseek_api_key="unit-test"), "提取", {"test": True}, image_urls=["data:image/jpeg;base64,YQ=="]), "{}")
            content = post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertEqual(content[1]["type"], "image_url")
        self.assertEqual(content[1]["image_url"], {"url": "data:image/jpeg;base64,YQ==", "detail": "original"})

    def test_unsupported_vision_error_is_clear_and_does_not_echo_provider_body(self):
        with patch("RAG.llm.httpx.Client") as client:
            client.return_value.__enter__.return_value.post.return_value = httpx.Response(400, text="private-provider-body")
            with self.assertRaises(HTTPException) as error:
                request_json(Settings(deepseek_api_key="unit-test"), "提取", {}, image_urls=["data:image/jpeg;base64,YQ=="])
        self.assertIn("未接受图片", error.exception.detail)
        self.assertNotIn("private-provider-body", error.exception.detail)
