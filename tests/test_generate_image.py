#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_image.py"
SPEC = importlib.util.spec_from_file_location("generate_image", SCRIPT_PATH)
assert SPEC and SPEC.loader
generate_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_image)


class FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self._body


class GenerateImageTests(unittest.TestCase):
    def test_provider_specific_model_resolution(self):
        self.assertEqual(generate_image.resolve_codex_model("gpt-5.6-sol"), "gpt-5.6-sol")
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch.object(generate_image.Path, "cwd", return_value=Path(temp_dir)),
            ):
                self.assertEqual(generate_image.resolve_codex_model(), generate_image.DEFAULT_CODEX_MODEL)

    def test_openai_settings_load_from_project_dotenv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, ".env.local").write_text(
                "OPENAI_IMAGE_API_KEY=dotenv-key\n"
                "OPENAI_IMAGE_BASE_URL=https://images.example.test/v1\n"
                "DRAW_CODEX_MODEL=gpt-image-2\n",
                encoding="utf-8",
            )
            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch.object(generate_image.Path, "cwd", return_value=Path(temp_dir)),
            ):
                self.assertEqual(generate_image.resolve_codex_api_key(), "dotenv-key")
                self.assertEqual(
                    generate_image.resolve_codex_base_url(), "https://images.example.test/v1"
                )
                self.assertEqual(generate_image.resolve_codex_api_style(), "images")
                self.assertEqual(generate_image.resolve_codex_model(), "gpt-image-2")

    def test_openai_base_url_is_explicit_and_normalized(self):
        with mock.patch.dict(os.environ, {"OPENAI_IMAGE_BASE_URL": "https://example.com"}, clear=False):
            self.assertEqual(generate_image.resolve_codex_base_url(), "https://example.com")
        with mock.patch.dict(
            os.environ, {"OPENAI_IMAGE_BASE_URL": "https://example.com/custom/v1/"}, clear=False
        ):
            self.assertEqual(generate_image.resolve_codex_base_url(), "https://example.com/custom/v1")

    def test_default_contract_requires_image_specific_url_and_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch.dict(os.environ, {"OPENAI_API_KEY": "generic-key"}, clear=True),
                mock.patch.object(generate_image.Path, "cwd", return_value=Path(temp_dir)),
            ):
                self.assertEqual(generate_image.resolve_codex_api_key(), "")
                self.assertEqual(generate_image.resolve_codex_base_url(), "")

            output = Path(temp_dir) / "result.png"
            with (
                mock.patch.dict(os.environ, {"OPENAI_IMAGE_API_KEY": "image-key"}, clear=True),
                mock.patch.object(generate_image.Path, "cwd", return_value=Path(temp_dir)),
            ):
                with self.assertRaisesRegex(RuntimeError, "No OPENAI_IMAGE_BASE_URL found"):
                    generate_image.request_codex_image(
                        prompt="draw a test",
                        refs=[],
                        image_type="wide",
                        model="gpt-image-2",
                        output_path=output,
                    )

    def test_cli_defaults_to_codex_images_contract(self):
        with mock.patch.object(
            generate_image.sys,
            "argv",
            ["generate_image.py", "--prompt", "draw a test"],
        ):
            args = generate_image.parse_args()

        self.assertEqual(args.provider, "codex")
        self.assertEqual(generate_image.resolve_codex_api_style(args.api_style), "images")
        self.assertEqual(args.type, "wide")
        self.assertEqual(generate_image.CODEX_SIZE_PRESETS[args.type], "1152x640")
        self.assertEqual(args.quality, "high")

    def test_explicit_responses_request_uses_selected_model_and_image_tool(self):
        captured = {}
        png = b"\x89PNG\r\n\x1a\nfixture"
        response_payload = {
            "output": [
                {
                    "type": "image_generation_call",
                    "result": base64.b64encode(png).decode("ascii"),
                }
            ]
        }

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(response_payload)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.png"
            with (
                mock.patch.dict(os.environ, {"OPENAI_IMAGE_API_KEY": "test-key"}, clear=False),
                mock.patch.object(generate_image.urllib.request, "urlopen", side_effect=fake_urlopen),
            ):
                final_path = generate_image.request_codex_image(
                    prompt="draw a test",
                    refs=[],
                    image_type="wide",
                    model="gpt-5.6-sol",
                    output_path=output,
                    api_style="responses",
                )

            request_payload = json.loads(captured["request"].data)
            self.assertEqual(request_payload["model"], "gpt-5.6-sol")
            self.assertEqual(request_payload["tool_choice"], "required")
            self.assertIs(request_payload["store"], False)
            self.assertEqual(request_payload["tools"][0]["size"], "1152x640")
            self.assertEqual(final_path.read_bytes(), png)
            self.assertEqual(captured["request"].headers["Authorization"], "Bearer test-key")

    def test_images_api_generation_uses_json_endpoint_and_b64_response(self):
        captured = {}
        png = b"\x89PNG\r\n\x1a\ngenerated"

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return FakeResponse({"data": [{"b64_json": base64.b64encode(png).decode("ascii")}]} )

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.png"
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "OPENAI_IMAGE_API_KEY": "test-key",
                        "OPENAI_IMAGE_BASE_URL": "https://images.example.test/v1",
                        "OPENAI_IMAGE_API_STYLE": "",
                    },
                    clear=False,
                ),
                mock.patch.object(generate_image.urllib.request, "urlopen", side_effect=fake_urlopen),
            ):
                final_path = generate_image.request_codex_image(
                    prompt="draw a test",
                    refs=[],
                    image_type="wide",
                    model="gpt-image-2",
                    output_path=output,
                )

            request = captured["request"]
            payload = json.loads(request.data)
            self.assertEqual(request.full_url, "https://images.example.test/v1/images/generations")
            self.assertEqual(payload["model"], "gpt-image-2")
            self.assertEqual(payload["size"], "1152x640")
            self.assertEqual(payload["quality"], "high")
            self.assertEqual(payload["response_format"], "b64_json")
            self.assertEqual(final_path.read_bytes(), png)
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            self.assertEqual(request.headers["Accept"], "application/json")
            self.assertEqual(request.headers["Content-type"], "application/json")

    def test_images_api_edit_uses_multipart_and_reference_field(self):
        captured = {}
        png = b"\x89PNG\r\n\x1a\nedited"

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return FakeResponse({"data": [{"b64_json": base64.b64encode(png).decode("ascii")}]} )

        with tempfile.TemporaryDirectory() as temp_dir:
            reference = Path(temp_dir) / "frame.png"
            reference.write_bytes(b"\x89PNG\r\n\x1a\nreference")
            output = Path(temp_dir) / "result.png"
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "OPENAI_IMAGE_API_KEY": "test-key",
                        "OPENAI_IMAGE_BASE_URL": "https://images.example.test/v1",
                        "OPENAI_IMAGE_FIELD": "image[]",
                    },
                    clear=False,
                ),
                mock.patch.object(generate_image.urllib.request, "urlopen", side_effect=fake_urlopen),
            ):
                final_path = generate_image.request_codex_image(
                    prompt="edit the frame",
                    refs=[reference],
                    image_type="wide",
                    model="gpt-image-2",
                    output_path=output,
                    api_style="images",
                    size="1152x640",
                    quality="high",
                )

            request = captured["request"]
            content_type = request.get_header("Content-type")
            body = request.data.decode("latin-1")
            self.assertEqual(request.full_url, "https://images.example.test/v1/images/edits")
            self.assertTrue(content_type.startswith("multipart/form-data; boundary="))
            self.assertIn('name="image[]"; filename="frame.png"', body)
            self.assertIn('name="size"\r\n\r\n1152x640', body)
            self.assertIn('name="quality"\r\n\r\nhigh', body)
            self.assertEqual(final_path.read_bytes(), png)


if __name__ == "__main__":
    unittest.main()
