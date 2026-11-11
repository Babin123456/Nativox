BASIC_VISEMES = {"p":"closed", "b":"closed", "m":"closed",
                 "a":"open", "aa":"open", "i":"wide", "ee":"wide",
                 "u":"rounded", "oo":"rounded", "o":"rounded"}
def phoneme_to_viseme(phoneme: str) -> str:
    return BASIC_VISEMES.get(phoneme.lower(), "neutral")
