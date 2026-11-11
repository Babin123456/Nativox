from pathlib import Path
import json, shutil, subprocess

def probe_video(path: Path):
    exe = shutil.which("ffprobe")
    if not exe:
        raise RuntimeError("Install FFmpeg (ffprobe) and add it to PATH.")
    r = subprocess.run([exe, "-v", "error", "-show_streams", "-show_format",
                        "-of", "json", str(path)], check=True, capture_output=True, text=True)
    data = json.loads(r.stdout)
    return {"duration": float(data.get("format", {}).get("duration", 0)),
            "format": data.get("format", {}).get("format_name"),
            "streams": [{"type": s.get("codec_type"), "codec": s.get("codec_name"),
                         "width": s.get("width"), "height": s.get("height")}
                        for s in data.get("streams", [])]}
