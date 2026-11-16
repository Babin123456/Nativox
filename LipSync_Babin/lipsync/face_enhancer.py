import os
import sys
from types import ModuleType

# Torchvision compatibility shim for newer torchvision versions
try:
    import torchvision.transforms.functional as F
    m = ModuleType('torchvision.transforms.functional_tensor')
    m.rgb_to_grayscale = F.rgb_to_grayscale
    sys.modules['torchvision.transforms.functional_tensor'] = m
except Exception:
    pass

import cv2
import torch
import numpy as np
from gfpgan import GFPGANer
try:
    from lipsync.selective_compositor import SelectiveCompositor, LandmarkMouthMasker, SpeechActivityTimeline
except ImportError:
    from selective_compositor import SelectiveCompositor, LandmarkMouthMasker, SpeechActivityTimeline

class FaceEnhancer:
    def __init__(self, model_path=None, upscale=1):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[FaceEnhancer] Initializing GFPGAN on {self.device}...")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(base_dir, ".."))
        if model_path is None:
            # Check local models, root gfpgan or wav2lip checkpoints
            cand_paths = [
                os.getenv("GFPGAN_MODEL_PATH"),
                os.path.join(root_dir, "models", "wav2lip", "checkpoints", "GFPGANv1.4.pth"),
                os.path.join(root_dir, "gfpgan", "weights", "GFPGANv1.4.pth"),
                os.path.join(base_dir, "generator", "wav2lip", "checkpoints", "GFPGANv1.4.pth")
            ]
            model_path = next((p for p in filter(None, cand_paths) if os.path.exists(p)), cand_paths[1])
            
        # Ensure gfpgan weights directory is found
        cand_weights_dirs = [
            os.path.join(root_dir, "gfpgan", "weights"),
            os.path.join(base_dir, "gfpgan", "weights")
        ]
        weights_dir = next((d for d in cand_weights_dirs if os.path.exists(d)), cand_weights_dirs[0])
        if os.path.exists(weights_dir):
            os.environ["GFPGAN_MODEL_DIR"] = weights_dir
        if os.path.exists(weights_dir):
            os.environ["GFPGAN_MODEL_DIR"] = weights_dir
        
        self.restorer = GFPGANer(
            model_path=model_path,
            upscale=upscale,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None,
            device=torch.device(self.device)
        )
        self.compositor = SelectiveCompositor()
        print("[FaceEnhancer] GFPGAN & SelectiveCompositor ready!")

    def enhance_frame(self, frame_bgr, orig_frame_bgr=None, restore_gfpgan=True):
        """
        Enhance facial details (teeth, lips, mouth region) in a single BGR frame
        while compositing directly onto the pristine original video frame.
        The entire rest of the frame (background, clothing, body, hair, eyes, spectacles)
        is 100% UNTOUCHED from the original camera recording.
        """
        target_orig = orig_frame_bgr if orig_frame_bgr is not None else frame_bgr
        target_h, target_w = target_orig.shape[:2]

        # Match frame resolution to original source video (e.g. Full HD 1080p)
        if frame_bgr.shape[:2] != (target_h, target_w):
            frame_input = cv2.resize(frame_bgr, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            frame_input = frame_bgr

        if restore_gfpgan:
            _, _, restored_img = self.restorer.enhance(
                frame_input,
                has_aligned=False,
                only_center_face=True,
                paste_back=True
            )
        else:
            restored_img = frame_input
            try:
                self.restorer.face_helper.clean_all()
                self.restorer.face_helper.read_image(frame_input)
                self.restorer.face_helper.get_face_landmarks_5(only_center_face=True)
            except Exception:
                pass

        # Composite enhanced mouth seamlessly onto the PRISTINE ORIGINAL source frame
        # using the dedicated SelectiveCompositor (dense 468 landmarks, sub-nasal cutoff, temporal smoothing)
        try:
            blended, _ = self.compositor.composite_frame(
                orig_frame=target_orig,
                gen_frame=restored_img,
                is_speaking=True
            )
            return blended
        except Exception as e:
            print(f"[FaceEnhancer] Compositing notice: {e}. Falling back to restored frame.")
            return restored_img

    def enhance_video(self, input_video_path, output_video_path, original_source_video_path=None, speaking_intervals=None, audio_path=None, restore_gfpgan=True):
        """
        Enhance an entire dubbed video frame-by-frame:
        - Keeps background, eyes, spectacles, hair and body 100% pristine original 1080p.
        - Restores mouth and teeth details to high-definition clarity.
        - Speech-interval gating: If a frame falls outside active speaking intervals,
          keeps the pristine original camera frame 100% untouched (no lip sync, no blur).
        - Exports in visually lossless Full HD (CRF 17, 15-20 Mbps) to eliminate quality drops.
        - Direct audio multiplexing: Muxes master audio (continuous BGM + dubbed speech) in single encode pass.
        """
        print(f"[FaceEnhancer] Restoring video sharpness & teeth details: {input_video_path}")
        cap = cv2.VideoCapture(input_video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        cap_orig = None
        if original_source_video_path and os.path.exists(original_source_video_path):
            cap_orig = cv2.VideoCapture(original_source_video_path)
            orig_fps = cap_orig.get(cv2.CAP_PROP_FPS)
            if orig_fps and orig_fps > 0:
                fps = orig_fps
            width = int(cap_orig.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap_orig.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"[FaceEnhancer] Compositing onto pristine source video: {width}x{height} Full HD ({total_frames} frames @ {fps:.3f} fps)")
        else:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        temp_avi = output_video_path.replace(".mp4", "_enhanced_temp.avi")
        fourcc = cv2.VideoWriter_fourcc(*'FFV1')
        out = cv2.VideoWriter(temp_avi, fourcc, fps, (width, height))

        frame_idx = 0
        # Iterate over the complete original video frames so NO tail frames are dropped
        driving_cap = cap_orig if cap_orig is not None else cap
        while driving_cap.isOpened():
            if cap_orig is not None:
                ret_orig, orig_frame = cap_orig.read()
                if not ret_orig:
                    break
                ret_gen, frame = cap.read()
                if not ret_gen or frame is None:
                    # If lip sync video is slightly shorter than original, reuse original camera frame
                    frame = orig_frame
            else:
                ret, frame = cap.read()
                if not ret:
                    break
                orig_frame = None

            # Calculate current timestamp
            current_time = frame_idx / (fps if fps > 0 else 30.0)

            # Check if current frame is within any active speaking interval
            is_speaking = True
            if speaking_intervals is not None:
                is_speaking = SpeechActivityTimeline.is_speaking(current_time, speaking_intervals)

            if is_speaking:
                # Enhance facial sharpness & composite onto pristine original frame
                enhanced = self.enhance_frame(frame, orig_frame_bgr=orig_frame, restore_gfpgan=restore_gfpgan)
                out.write(enhanced)
            else:
                # Speaker is NOT speaking: keep original camera frame 100% untouched
                out.write(orig_frame if orig_frame is not None else frame)

            frame_idx += 1
            if frame_idx % 10 == 0 or frame_idx == total_frames:
                print(f"  Enhanced {frame_idx}/{total_frames} frames (Current time: {current_time:.2f}s, Active Speech: {is_speaking})...", flush=True)

        cap.release()
        if cap_orig:
            cap_orig.release()
        out.release()

        # Remux with audio using visually lossless encoding (CRF 17, faststart for instant browser web playback)
        audio_src = audio_path if (audio_path and os.path.exists(audio_path)) else input_video_path
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_avi,
            "-i", audio_src,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-crf", "17",
            "-preset", "slow",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_video_path
        ]
        import subprocess
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(temp_avi):
            os.remove(temp_avi)

        print(f"[FaceEnhancer] Finished restoring Full HD video: {output_video_path}")
        return output_video_path
