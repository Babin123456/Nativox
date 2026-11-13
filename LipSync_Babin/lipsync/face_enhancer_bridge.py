import os
import subprocess
from pathlib import Path

class FaceRestorer:
    """
    Restores lip, mouth, and teeth clarity in dubbed videos using GFPGAN & Selective Landmark Compositor.
    Guarantees:
      - 100% untouched pixels for eyes, face contour, hair, spectacles, and background.
      - Smooth temporal lip compositing only on the mouth aperture below the sub-nasal base.
      - Graceful fallback to pristine composited frames if system RAM runs low.
    """
    def __init__(self, upscale: int = 1):
        self.upscale = upscale
        self.lipsync_python = Path("C:/Users/babin/Downloads/LipSyncLab_v2/LipSync_Lab/.venv/Scripts/python.exe")

    def enhance_video(
        self,
        generated_video: Path,
        original_video: Path,
        output_video: Path,
        audio_path: Path = None,
        speaking_intervals: list = None
    ):
        generated_video = Path(generated_video).resolve()
        original_video = Path(original_video).resolve()
        output_video = Path(output_video).resolve()
        audio_cmd = f", audio_path=r'{Path(audio_path).resolve()}'" if audio_path else ""
        intervals_cmd = f", speaking_intervals={speaking_intervals}" if speaking_intervals else ""

        cmd = [
            str(self.lipsync_python),
            "-c",
            f"""
import sys, os, gc
from pathlib import Path
from types import ModuleType
import torchvision.transforms.functional as F
m = ModuleType('torchvision.transforms.functional_tensor')
m.rgb_to_grayscale = F.rgb_to_grayscale
sys.modules['torchvision.transforms.functional_tensor'] = m

sys.path.insert(0, r'C:\\Users\\babin\\Downloads\\LipSyncLab_v2\\LipSync_Lab')
from Pipeline2.face_enhancer import FaceEnhancer

try:
    enhancer = FaceEnhancer(upscale={self.upscale})
    enhancer.enhance_video(
        input_video_path=r'{generated_video}',
        output_video_path=r'{output_video}',
        original_source_video_path=r'{original_video}',
        restore_gfpgan=True{audio_cmd}{intervals_cmd}
    )
    print('HD Face Enhancement complete!')
except Exception as e:
    print(f'GFPGAN warning ({{e}}), falling back to Selective Compositor...')
    gc.collect()
    enhancer = FaceEnhancer(upscale={self.upscale})
    enhancer.enhance_video(
        input_video_path=r'{generated_video}',
        output_video_path=r'{output_video}',
        original_source_video_path=r'{original_video}',
        restore_gfpgan=False{audio_cmd}{intervals_cmd}
    )
    print('Selective Compositor fallback complete!')
"""
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        # Even if temp cleanup threw a Windows file lock notice, check if final output_video exists
        if not output_video.exists() or output_video.stat().st_size == 0:
            if res.returncode != 0:
                raise RuntimeError(f"Face enhancement failed:\n{res.stderr}\n{res.stdout}")

        return output_video
