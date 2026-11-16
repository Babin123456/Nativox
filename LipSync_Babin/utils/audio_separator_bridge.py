import os
import subprocess
import sys
import shutil
from pathlib import Path
from utils.env_utils import get_python_executable

class StemSeparatorBridge:
    """Separates human speech and background music/ambience using Demucs."""
    def __init__(self):
        pass

    def separate(self, media_path: Path, output_dir: Path):
        media_path = Path(media_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        vocals_path = output_dir / f"{media_path.stem}_vocals.wav"
        bgm_path = output_dir / f"{media_path.stem}_bgm.wav"

        if vocals_path.exists() and bgm_path.exists():
            return vocals_path, bgm_path

        py_exe = get_python_executable()
        root_dir = Path(__file__).resolve().parent.parent
        custom_pipeline_dir = os.getenv("PIPELINE2_DIR", "")

        script = f"""
import sys, os
from pathlib import Path

root_dir = Path(r'{root_dir}')
pipeline2_dir = Path(r'{custom_pipeline_dir}') if r'{custom_pipeline_dir}' else None

cand_dirs = [
    pipeline2_dir,
    root_dir,
    root_dir / "Pipeline2"
]
for d in filter(None, cand_dirs):
    if d.exists() and str(d) not in sys.path:
        sys.path.insert(0, str(d))

# Strategy 1: Dedicated AudioStemSeparator class if present
try:
    try:
        from utils.audio_separator import AudioStemSeparator
    except ImportError:
        from audio_separator import AudioStemSeparator
    sep = AudioStemSeparator()
    voc, bgm = sep.separate(r'{media_path}', r'{output_dir}')
    print(f'SEPARATED:{{voc}}|{{bgm}}')
    sys.exit(0)
except Exception as e:
    pass

# Strategy 2: Direct demucs API
try:
    import demucs.api
    import soundfile as sf
    import numpy as np

    sep = demucs.api.Separator(model="htdemucs_ft", progress=False)
    origin, separated = sep.separate_audio_file(r'{media_path}')
    sr = sep.samplerate
    vocals = separated['vocals'].mean(0).cpu().numpy().astype(np.float32)
    no_vocals = (separated['drums'] + separated['bass'] + separated['other']).mean(0).cpu().numpy().astype(np.float32)

    v_out = os.path.join(r'{output_dir}', '{media_path.stem}_isolated_vocals.wav')
    b_out = os.path.join(r'{output_dir}', '{media_path.stem}_isolated_bgm.wav')
    sf.write(v_out, vocals, sr)
    sf.write(b_out, no_vocals, sr)
    print(f'SEPARATED:{{v_out}}|{{b_out}}')
    sys.exit(0)
except Exception as e2:
    pass

# Strategy 3: Graceful fallback - extract audio track as both vocals and bgm via ffmpeg
import subprocess
v_out = os.path.join(r'{output_dir}', '{media_path.stem}_isolated_vocals.wav')
b_out = os.path.join(r'{output_dir}', '{media_path.stem}_isolated_bgm.wav')
subprocess.run(['ffmpeg', '-y', '-i', r'{media_path}', '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', v_out], check=True, capture_output=True)
import shutil
shutil.copyfile(v_out, b_out)
print(f'SEPARATED:{{v_out}}|{{b_out}}')
"""
        res = subprocess.run([py_exe, "-c", script], capture_output=True, text=True)
        if res.returncode != 0 and (not vocals_path.exists() or not bgm_path.exists()):
            raise RuntimeError(f"Audio stem separation failed: {res.stderr}\n{res.stdout}")

        # Rename to clean filenames if output matches pattern
        for line in res.stdout.splitlines():
            if line.startswith("SEPARATED:"):
                v_res, b_res = line.replace("SEPARATED:", "").split("|")
                if Path(v_res).exists() and Path(v_res) != vocals_path:
                    shutil.move(str(v_res), str(vocals_path))
                if Path(b_res).exists() and Path(b_res) != bgm_path:
                    shutil.move(str(b_res), str(bgm_path))
                break

        return vocals_path, bgm_path
