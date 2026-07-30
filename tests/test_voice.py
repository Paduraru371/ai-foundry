"""Voice endpoint behavior without making paid Azure Speech calls."""
from __future__ import annotations

from io import BytesIO
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

from fastapi import UploadFile

from backend.api.routers.tools import speak, transcribe
from backend.services import speech
from backend.schemas import SpeakRequest


class TextToSpeechTests(TestCase):
    @patch(
        "backend.api.routers.tools.speech.synthesize",
        return_value=b"RIFF-test-audio",
    )
    def test_speak_returns_wav(self, synthesize) -> None:
        response = speak(SpeakRequest(text="Hello"))

        self.assertEqual(response.media_type, "audio/wav")
        self.assertEqual(response.body, b"RIFF-test-audio")
        synthesize.assert_called_once_with("Hello", None)


class SpeechToTextTests(IsolatedAsyncioTestCase):
    @patch(
        "backend.api.routers.tools.speech.transcribe",
        return_value={
            "status": "Success",
            "text": "What is my application status?",
            "confidence": 0.97,
            "duration_seconds": 2.1,
            "language": "en-US",
        },
    )
    async def test_transcribe_accepts_browser_wav(self, recognize) -> None:
        upload = UploadFile(
            filename="question.wav",
            file=BytesIO(b"RIFF-browser-audio"),
            headers={"content-type": "audio/wav"},
        )

        response = await transcribe(upload)

        self.assertEqual(response.text, "What is my application status?")
        recognize.assert_called_once_with(
            b"RIFF-browser-audio",
            content_type="audio/wav",
        )


class SpeechHealthTests(TestCase):
    def test_health_describes_tts_and_stt_separately(self) -> None:
        with patch(
            "backend.services.speech._credentials",
            return_value=("secret", "https://speech.example", "westeurope"),
        ):
            result = speech.describe()

        self.assertTrue(result["tts"]["configured"])
        self.assertTrue(result["stt"]["configured"])
