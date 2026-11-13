import argparse
import logging
from pathlib import Path
from config import PipelineConfig
from utils.video_utils import probe_video
from utils.audio_utils import extract_audio, mix_dialogue_with_background
from utils.duration_aligner import DurationAligner
from utils.audio_separator_bridge import StemSeparatorBridge
from translation.syllable_translator import SyllableAwareTranslator
from synthesis.sarvam_adapter import SarvamAdapter
from synthesis.edgetts_adapter import EdgeTTSAdapter
from synthesis.tone_transfer_bridge import ToneTransferBridge
from lipsync.wav2lip_engine import Wav2LipEngine
from lipsync.face_enhancer_bridge import FaceRestorer
from speech_analysis.transfer_engine import PerformanceTransferEngine

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def run_pipeline(cfg: PipelineConfig, enhance_face: bool = True, tts_backend: str = "sarvam", preserve_bgm: bool = True):
    if not cfg.input_video.exists():
        raise FileNotFoundError(f"Input video not found: {cfg.input_video}")
        
    info = probe_video(cfg.input_video)
    logging.info("Input media probed: %s", info)
    
    if cfg.dry_run:
        logging.info("Dry run successful. Target language: %s", cfg.target_lang)
        return

    cfg.work_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_video.parent.mkdir(parents=True, exist_ok=True)

    # 1. Audio & Stem Separation (Isolating human dialogue from background music/SFX)
    source_audio = cfg.work_dir / f"{cfg.input_video.stem}_source.wav"
    logging.info("Stage 1: Extracting master audio from video...")
    extract_audio(cfg.input_video, source_audio)

    bgm_audio = None
    speech_reference = source_audio
    if preserve_bgm:
        logging.info("Stage 1b: Running Demucs Neural Separation (Isolating Vocals & Preserving Continuous BGM)...")
        separator = StemSeparatorBridge()
        vocals_audio, bgm_audio = separator.separate(source_audio, cfg.work_dir)
        speech_reference = vocals_audio
        logging.info("Separated Vocal Track: %s", vocals_audio)
        logging.info("Preserved BGM Track: %s", bgm_audio)

    # 2. Transcription (Speech-to-Text on isolated speech)
    logging.info("Stage 2: Transcribing isolated speech via Sarvam Saaras API...")
    from translation.translator import build_translator
    translator = build_translator()
    transcript = translator.transcribe(speech_reference)
    logging.info("Transcript: '%s'", transcript)

    # 3. Syllable & Duration-Constrained Colloquial Translation
    target_duration = info.get("duration", 8.0)
    logging.info("Stage 3: Generating Syllable-Constrained translation (Target: %.2fs)...", target_duration)
    syllable_tr = SyllableAwareTranslator()
    translated_text = syllable_tr.translate_constrained(
        text=transcript,
        target_lang=cfg.target_lang,
        target_seconds=target_duration
    )
    logging.info("Translated text (%s): '%s'", cfg.target_lang, translated_text)

    # 4. Voice Synthesis & Speaker Performance Voice Transfer
    dubbed_speech = cfg.work_dir / f"cloned_speech_{cfg.target_lang}.wav"
    logging.info("Stage 4: Synthesizing voice via %s...", tts_backend.upper())
    raw_tts_audio = cfg.work_dir / f"raw_tts_{cfg.target_lang}.wav"
    if tts_backend == "sarvam" and os.getenv("SARVAM_API_KEY"):
        tts = SarvamAdapter()
    else:
        # Default Primary Zero-API EdgeTTS (100% Free / Zero API Keys)
        tts = EdgeTTSAdapter()
        
    tts.synthesize(
        text=translated_text,
        target_lang=cfg.target_lang,
        speaker_audio=str(speech_reference),
        output_path=raw_tts_audio
    )

    # 4b. Speaker Tone, Formant & Pitch Transfer (Matching original speaker's exact voice timbre via OpenVoice V2)
    raw_morphed = cfg.work_dir / f"morphed_speech_raw_{cfg.target_lang}.wav"
    logging.info("Stage 4b: Transferring original speaker vocal tract timbre, formant resonance & pitch...")
    base_speaker = "hi-IN-MadhurNeural" if cfg.target_lang == "hi" else "bn-IN-BashkarNeural"
    tone_engine = ToneTransferBridge()
    tone_engine.transfer_speaker_voice(
        synthesized_audio=raw_tts_audio,
        reference_speech_audio=speech_reference,
        output_audio=raw_morphed,
        base_speaker_name=base_speaker
    )
    dubbed_speech = raw_morphed

    # 4c. Duration & Speech Boundary Alignment (Prevent fake lip sync during leading/trailing pauses)
    final_aligned_speech = cfg.work_dir / f"morphed_speech_{cfg.target_lang}.wav"
    t_start, t_end = DurationAligner.detect_speech_boundaries(speech_reference)
    logging.info("Stage 4c: Speech activity detected between %.2fs and %.2fs (Total Video: %.2fs)", t_start, t_end, target_duration)
    logging.info("Aligning speech duration and padding leading (%.2fs) & trailing silence...", t_start)
    DurationAligner.align_duration_to_video(
        speech_wav=dubbed_speech,
        target_duration_s=target_duration,
        output_wav=final_aligned_speech,
        t_start_s=t_start,
        t_end_s=t_end
    )
    speaking_intervals = [(t_start, t_end)] if t_end > t_start else None

    # 4d. Master Audio Mixing (Dubbed dialogue + preserved original BGM)
    final_dubbed_audio = final_aligned_speech
    if bgm_audio and bgm_audio.exists():
        final_dubbed_audio = cfg.work_dir / f"master_audio_{cfg.target_lang}.wav"
        logging.info("Stage 4d: Mixing dubbed dialogue with preserved original BGM into master audio...")
        mix_dialogue_with_background(background=bgm_audio, dialogue=final_aligned_speech, output=final_dubbed_audio)

    # 5. Neural Lip Generation with Wav2Lip
    raw_dubbed_video = cfg.work_dir / f"wav2lip_raw_{cfg.target_lang}.mp4"
    logging.info("Stage 5: Running Wav2Lip neural lip synchronization...")
    wav2lip = Wav2LipEngine()
    wav2lip.generate(
        video_segment=cfg.input_video,
        dubbed_audio=final_aligned_speech,
        output_video=raw_dubbed_video
    )

    # 6. HD Face Enhancement & Selective Mouth Compositing (GFPGAN + Landmark Masking)
    if enhance_face:
        logging.info("Stage 6: Restoring high-definition lip, mouth & teeth details via GFPGAN & Selective Compositor...")
        restorer = FaceRestorer(upscale=1)
        restorer.enhance_video(
            generated_video=raw_dubbed_video,
            original_video=cfg.input_video,
            output_video=cfg.output_video,
            audio_path=final_dubbed_audio,
            speaking_intervals=speaking_intervals
        )
    else:
        # Merge final audio into raw dubbed video
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_dubbed_video), "-i", str(final_dubbed_audio),
            "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", str(cfg.output_video)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 7. Speaker Performance Evaluation (A/V Sync, MAR-RMS correlation, Identity stability)
    logging.info("Stage 7: Evaluating Audiovisual Performance Transfer Quality...")
    spte = PerformanceTransferEngine(output_dir=cfg.work_dir / "spm")
    spte.evaluate_audiovisual_quality(
        dubbed_video=cfg.output_video,
        target_audio=final_dubbed_audio,
        target_lang=cfg.target_lang
    )

    logging.info("Pipeline completed successfully! Output: %s", cfg.output_video)

def main():
    p = argparse.ArgumentParser(description="Nativox multilingual dubbing pipeline")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--lang", required=True, choices=["hi", "bn"])
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--work-dir", type=Path, default=Path("work"))
    p.add_argument("--tts", default="free", choices=["free", "edgetts", "sarvam"])
    p.add_argument("--enhance", action="store_true", default=True, help="Enhance face with GFPGAN and selective compositor")
    p.add_argument("--no-enhance", dest="enhance", action="store_false")
    p.add_argument("--preserve-bgm", action="store_true", default=True, help="Preserve original background music and sound effects")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    
    cfg = PipelineConfig(a.input, a.lang, a.output, a.work_dir, a.dry_run)
    run_pipeline(cfg, enhance_face=a.enhance, tts_backend=a.tts, preserve_bgm=a.preserve_bgm)

if __name__ == "__main__":
    main()
