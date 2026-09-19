"""
Test suite for Stage 6: Hindi Text to MP3 (edge-tts synthesis).

Run with:
    python -m pytest test_tts.py -v
"""

import os
import sys

import pytest

# Ensure the backend directory is on the path so 'app' can be imported
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── Health Endpoint ────────────────────────────────────────────────────────


class TestHealth:
    """Verify the health endpoint responds correctly."""

    def test_health_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_contains_service_name(self):
        data = client.get("/api/health").json()
        assert data["service"] == "stage-6-text-to-mp3"

    def test_health_contains_engine(self):
        data = client.get("/api/health").json()
        assert data["engine"] == "edge-tts"


# ── Voice Listing ──────────────────────────────────────────────────────────


class TestVoiceListing:
    """Verify voice listing returns Hindi voices."""

    def test_voices_returns_200(self):
        response = client.get("/api/voices")
        assert response.status_code == 200

    def test_voices_returns_hindi_voices(self):
        data = client.get("/api/voices").json()
        assert data["count"] >= 2
        short_names = [v["short_name"] for v in data["voices"]]
        assert "hi-IN-SwaraNeural" in short_names
        assert "hi-IN-MadhurNeural" in short_names

    def test_voices_have_gender_info(self):
        data = client.get("/api/voices").json()
        for voice in data["voices"]:
            assert voice["gender"] in ("Female", "Male", "Unknown")


# ── Synthesis Validation ───────────────────────────────────────────────────


class TestSynthesisValidation:
    """Verify input validation for the synthesize endpoint."""

    def test_empty_text_returns_422(self):
        response = client.post(
            "/api/synthesize",
            json={"text": "", "voice": "hi-IN-SwaraNeural"},
        )
        # Pydantic min_length=1 rejects empty strings with 422
        assert response.status_code == 422

    def test_missing_text_returns_422(self):
        response = client.post("/api/synthesize", json={})
        assert response.status_code == 422


# ── Synthesis (Integration) ────────────────────────────────────────────────


class TestSynthesisIntegration:
    """
    Integration tests that call the real edge-tts engine.

    These tests require an internet connection (edge-tts uses
    Microsoft's online Neural TTS service).
    """

    @pytest.mark.skipif(
        os.environ.get("SKIP_INTEGRATION") == "1",
        reason="Integration tests disabled via SKIP_INTEGRATION=1",
    )
    def test_synthesize_hindi_text(self):
        """Synthesize a short Hindi sentence and verify MP3 is returned."""
        response = client.post(
            "/api/synthesize",
            json={
                "text": "नमस्ते, यह एक परीक्षण है।",
                "voice": "hi-IN-SwaraNeural",
                "rate": "+0%",
                "pitch": "+0Hz",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["voice_used"] == "hi-IN-SwaraNeural"
        assert data["text_length"] > 0
        assert data["word_count"] > 0
        assert data["audio_url"].startswith("/api/audio/")

        # Verify the audio file is actually downloadable
        audio_response = client.get(data["audio_url"])
        assert audio_response.status_code == 200
        assert audio_response.headers["content-type"] == "audio/mpeg"
        # MP3 files start with ID3 tag or FF FB sync bytes
        audio_bytes = audio_response.content
        assert len(audio_bytes) > 1000, "MP3 file is suspiciously small"

    @pytest.mark.skipif(
        os.environ.get("SKIP_INTEGRATION") == "1",
        reason="Integration tests disabled via SKIP_INTEGRATION=1",
    )
    def test_synthesize_english_text(self):
        """Verify English text also synthesizes (for pipeline flexibility)."""
        response = client.post(
            "/api/synthesize",
            json={
                "text": "Hello, this is a test of the speech synthesis engine.",
                "voice": "hi-IN-MadhurNeural",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["voice_used"] == "hi-IN-MadhurNeural"

    @pytest.mark.skipif(
        os.environ.get("SKIP_INTEGRATION") == "1",
        reason="Integration tests disabled via SKIP_INTEGRATION=1",
    )
    def test_synthesize_with_rate_adjustment(self):
        """Verify rate adjustment parameter works."""
        response = client.post(
            "/api/synthesize",
            json={
                "text": "गति परीक्षण",
                "voice": "hi-IN-SwaraNeural",
                "rate": "+20%",
            },
        )
        assert response.status_code == 200


# ── Audio Serving ──────────────────────────────────────────────────────────


class TestAudioServing:
    """Verify audio file serving endpoint."""

    def test_nonexistent_audio_returns_404(self):
        response = client.get("/api/audio/nonexistent_file.mp3")
        assert response.status_code == 404

    def test_directory_traversal_blocked(self):
        response = client.get("/api/audio/../../etc/passwd")
        assert response.status_code == 404


# ── Frontend Serving ───────────────────────────────────────────────────────


class TestFrontend:
    """Verify frontend is served."""

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200
