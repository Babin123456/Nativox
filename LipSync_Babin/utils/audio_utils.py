from pathlib import Path
import shutil, subprocess

def ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("Install FFmpeg and add it to PATH.")
    return exe

def extract_audio(video: Path, output: Path, sample_rate=48000):
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg(), "-y", "-i", str(video), "-vn", "-ac", "2",
                    "-ar", str(sample_rate), "-c:a", "pcm_s16le", str(output)],
                   check=True, capture_output=True)
    return output

def mix_dialogue_with_background(background: Path, dialogue: Path, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg(), "-y", "-i", str(background), "-i", str(dialogue),
                    "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first[a]",
                    "-map", "[a]", str(output)], check=True, capture_output=True)
    return output
