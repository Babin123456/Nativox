import os
import subprocess
from pathlib import Path

class PerformanceTransferEngine:
    """
    Speaker Performance Transfer Engine (SPTE):
    Extracts vocal dynamics (pitch, energy, pauses) and facial performance (landmarks, head pose),
    synthesizes performance-matched speech, and runs full audiovisual QA evaluation.
    """
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lipsync_python = Path(os.getenv("LIPSYNC_PYTHON", "python"))

    def extract_performance(self, video_path: Path, gender: str = "male"):
        """Extracts Vocal and Facial Performance Memory."""
        video_path = Path(video_path).resolve()
        script = f"""
import sys
from pathlib import Path
sys.path.insert(0, r'{Path(".").resolve()}')
if 'LIPSYNC_LAB_DIR' in os.environ:
    sys.path.insert(0, os.environ['LIPSYNC_LAB_DIR'])

from speech_analysis.spm.vocal_performance import VocalPerformanceAnalyzer
from speech_analysis.spm.facial_performance import FacialPerformanceAnalyzer
from speech_analysis.spm.performance_memory import PerformanceMemory
from speech_analysis.spm.schema import SPMData

vocal_analyzer = VocalPerformanceAnalyzer()
facial_analyzer = FacialPerformanceAnalyzer(sample_every_n_frames=2)

print('Extracting vocal dynamics...')
vp = vocal_analyzer.analyze(r'{video_path}', speaker_gender='{gender}')

print('Extracting facial performance & 468 landmarks...')
fp = facial_analyzer.analyze(r'{video_path}')

spm_data = SPMData(
    video_stem='{video_path.stem}',
    vocal_performance=vp,
    facial_performance=fp
)

pm = PerformanceMemory(output_dir=r'{self.output_dir}')
save_path = pm.save(spm_data)
print(f'Performance Memory saved to: {{save_path}}')
"""
        res = subprocess.run([str(self.lipsync_python), "-c", script], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[Warning] SPM Extraction warning: {res.stderr}")
        else:
            print("[SPTE] Successfully extracted and saved Speaker Performance Memory!")

    def evaluate_audiovisual_quality(self, dubbed_video: Path, target_audio: Path, target_lang: str):
        """Runs Independent Audio-Visual Quality Evaluation (SyncNet, MAR-RMS correlation, face stability)."""
        dubbed_video = Path(dubbed_video).resolve()
        target_audio = Path(target_audio).resolve()
        script = f"""
import sys, json, os
from pathlib import Path
sys.path.insert(0, r'{Path(".").resolve()}')
if 'LIPSYNC_LAB_DIR' in os.environ:
    sys.path.insert(0, os.environ['LIPSYNC_LAB_DIR'])

from speech_analysis.spm.quality_evaluator import QualityEvaluator

evaluator = QualityEvaluator(output_dir=r'{self.output_dir}')
report = evaluator.evaluate(
    dubbed_video_path=r'{dubbed_video}',
    target_audio_path=r'{target_audio}',
    source_spm=None,
    target_analysis=None,
    video_stem='{dubbed_video.stem}',
    target_lang='{target_lang}'
)

print('Audiovisual Evaluation Report:')
print(json.dumps(report, indent=2))
"""
        res = subprocess.run([str(self.lipsync_python), "-c", script], capture_output=True, text=True)
        if res.returncode == 0:
            print(res.stdout)
        else:
            print(f"[Warning] Evaluation note: {res.stderr}")
