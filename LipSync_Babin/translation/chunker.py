from dataclasses import dataclass

@dataclass
class TranslationChunk:
    start_time: float
    end_time: float
    text: str
    emotion: str = "unknown"

def chunk_translation(segments):
    return [TranslationChunk(s.start_time, s.end_time, s.translated_text, s.emotion)
            for s in segments if s.translated_text.strip()]
