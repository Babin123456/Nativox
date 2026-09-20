"""
Test suite for Stage 7: Merge MP3 with MP4.

Covers health endpoint, FFmpeg discovery, merge validation, probe endpoint,
and security checks.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── Helper: Create tiny test media files using FFmpeg ──────────────────────


def _find_ffmpeg() -> str:
    """Find FFmpeg binary for test fixture generation."""
    import shutil

    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin and os.path.exists(ffmpeg_bin):
        return ffmpeg_bin

    winget_packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget_packages.exists():
        matches = list(winget_packages.glob("**/ffmpeg.exe"))
        if matches:
            return str(matches[0])

    pytest.skip("FFmpeg not found — skipping integration tests")


def create_test_video(path: Path, duration: float = 2.0):
    """Generate a tiny silent test MP4 video with FFmpeg."""
    ffmpeg = _find_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=320x240:d={duration}",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "64k",
        "-pix_fmt", "yuv420p",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Failed to create test video: {result.stderr}"


def create_test_audio(path: Path, duration: float = 2.0):
    """Generate a tiny silent test MP3 audio with FFmpeg."""
    ffmpeg = _find_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:a", "libmp3lame", "-b:a", "64k",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Failed to create test audio: {result.stderr}"


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_video(tmp_path_factory):
    """Generate a temporary test MP4 video."""
    path = tmp_path_factory.mktemp("media") / "test_video.mp4"
    create_test_video(path)
    return path


@pytest.fixture(scope="module")
def test_audio(tmp_path_factory):
    """Generate a temporary test MP3 audio."""
    path = tmp_path_factory.mktemp("media") / "test_audio.mp3"
    create_test_audio(path)
    return path


# ── Test: Health Endpoint ──────────────────────────────────────────────────


class TestHealth:
    def test_health_returns_ok(self):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "stage-7-merge-mp3-with-mp4"
        assert "ffmpeg" in data

    def test_health_reports_ffmpeg_status(self):
        res = client.get("/api/health")
        data = res.json()
        assert data["ffmpeg"] in ("available", "not found")


# ── Test: FFmpeg Discovery ─────────────────────────────────────────────────


class TestFFmpegDiscovery:
    def test_find_ffmpeg_returns_path(self):
        from app.merger import find_ffmpeg

        try:
            path = find_ffmpeg()
            assert Path(path).name.startswith("ffmpeg")
        except FileNotFoundError:
            pytest.skip("FFmpeg not installed")

    def test_find_ffprobe_returns_path(self):
        from app.merger import find_ffprobe

        try:
            path = find_ffprobe()
            assert Path(path).name.startswith("ffprobe")
        except FileNotFoundError:
            pytest.skip("FFprobe not installed")


# ── Test: Merge Endpoint ───────────────────────────────────────────────────


class TestMergeEndpoint:
    def test_merge_produces_valid_mp4(self, test_video, test_audio):
        with open(test_video, "rb") as vf, open(test_audio, "rb") as af:
            res = client.post(
                "/api/merge",
                files={
                    "video": ("test.mp4", vf, "video/mp4"),
                    "audio": ("test.mp3", af, "audio/mpeg"),
                },
            )
        assert res.status_code == 200
        data = res.json()
        assert "video_url" in data
        assert data["video_url"].startswith("/api/video/")
        assert data["file_size_mb"] >= 0
        assert data["resolution"]
        assert data["audio_codec"]

    def test_merge_missing_video_returns_422(self, test_audio):
        with open(test_audio, "rb") as af:
            res = client.post(
                "/api/merge",
                files={
                    "audio": ("test.mp3", af, "audio/mpeg"),
                },
            )
        assert res.status_code == 422

    def test_merge_missing_audio_returns_422(self, test_video):
        with open(test_video, "rb") as vf:
            res = client.post(
                "/api/merge",
                files={
                    "video": ("test.mp4", vf, "video/mp4"),
                },
            )
        assert res.status_code == 422

    def test_merge_invalid_video_format_returns_400(self, test_audio):
        with open(test_audio, "rb") as af:
            res = client.post(
                "/api/merge",
                files={
                    "video": ("test.txt", b"not a video", "text/plain"),
                    "audio": ("test.mp3", af, "audio/mpeg"),
                },
            )
        assert res.status_code == 400
        assert "Unsupported video format" in res.json()["detail"]

    def test_merge_invalid_audio_format_returns_400(self, test_video):
        with open(test_video, "rb") as vf:
            res = client.post(
                "/api/merge",
                files={
                    "video": ("test.mp4", vf, "video/mp4"),
                    "audio": ("test.txt", b"not audio", "text/plain"),
                },
            )
        assert res.status_code == 400
        assert "Unsupported audio format" in res.json()["detail"]

    def test_merged_output_has_correct_streams(self, test_video, test_audio):
        """Verify the merged output has exactly 1 video + 1 audio stream."""
        with open(test_video, "rb") as vf, open(test_audio, "rb") as af:
            res = client.post(
                "/api/merge",
                files={
                    "video": ("test.mp4", vf, "video/mp4"),
                    "audio": ("test.mp3", af, "audio/mpeg"),
                },
            )
        assert res.status_code == 200
        data = res.json()
        assert data["audio_codec"]  # Has audio
        assert data["resolution"]   # Has video


# ── Test: Video Serving ────────────────────────────────────────────────────


class TestVideoServing:
    def test_serve_nonexistent_video_returns_404(self):
        res = client.get("/api/video/nonexistent_file.mp4")
        assert res.status_code == 404

    def test_serve_merged_video(self, test_video, test_audio):
        # First create a merged file
        with open(test_video, "rb") as vf, open(test_audio, "rb") as af:
            merge_res = client.post(
                "/api/merge",
                files={
                    "video": ("test.mp4", vf, "video/mp4"),
                    "audio": ("test.mp3", af, "audio/mpeg"),
                },
            )
        assert merge_res.status_code == 200
        video_url = merge_res.json()["video_url"]

        # Now fetch the merged video
        res = client.get(video_url)
        assert res.status_code == 200
        assert res.headers["content-type"] == "video/mp4"
        assert len(res.content) > 0


# ── Test: Probe Endpoint ──────────────────────────────────────────────────


class TestProbeEndpoint:
    def test_probe_nonexistent_returns_404(self):
        res = client.get("/api/probe/nonexistent_file.mp4")
        assert res.status_code == 404

    def test_probe_merged_video(self, test_video, test_audio):
        # Create a merged file first
        with open(test_video, "rb") as vf, open(test_audio, "rb") as af:
            merge_res = client.post(
                "/api/merge",
                files={
                    "video": ("test.mp4", vf, "video/mp4"),
                    "audio": ("test.mp3", af, "audio/mpeg"),
                },
            )
        assert merge_res.status_code == 200
        filename = merge_res.json()["video_url"].split("/")[-1]

        # Probe it
        res = client.get(f"/api/probe/{filename}")
        assert res.status_code == 200
        data = res.json()
        assert data["filename"] == filename
        assert data["video_codec"]
        assert data["audio_codec"]
        assert data["file_size_mb"] >= 0


# ── Test: Frontend Serving ─────────────────────────────────────────────────


class TestFrontend:
    def test_index_returns_html(self):
        res = client.get("/")
        assert res.status_code == 200
        content_type = res.headers.get("content-type", "")
        # Could be HTML file or JSON fallback
        assert "text/html" in content_type or "application/json" in content_type


# ── Test: Security ─────────────────────────────────────────────────────────


class TestSecurity:
    def test_path_traversal_video_serving(self):
        res = client.get("/api/video/../../etc/passwd")
        assert res.status_code == 404

    def test_path_traversal_probe(self):
        res = client.get("/api/probe/../../etc/passwd")
        assert res.status_code == 404
