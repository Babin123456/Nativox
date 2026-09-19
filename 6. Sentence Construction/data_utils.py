"""
data_utils.py
-------------
Document extraction, sentence segmentation, and destructive sentence
corruption engine for training sentence construction models.

Supports:
  - PDF files (.pdf) via pypdf
  - Word files (.docx) via python-docx
  - Plain text files (.txt)
  - Entire directories of mixed documents
"""

import os
import re
import random
from typing import List, Tuple, Optional
import torch
from torch.utils.data import Dataset


# Common English function words frequently omitted or misplaced in destructive sentences
ARTICLES = {"a", "an", "the"}
PREPOSITIONS = {
    "in", "on", "at", "to", "for", "with", "by", "from", "about",
    "into", "through", "after", "over", "between", "under", "against"
}
AUXILIARY_VERBS = {
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "may", "might", "can", "could", "must"
}
CONJUNCTIONS = {"and", "but", "or", "so", "because", "although", "while", "if"}


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from all pages of a PDF document."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required to parse PDF documents. Install via `pip install pypdf`.")

    reader = PdfReader(pdf_path)
    text_chunks = []
    for page_idx, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            text_chunks.append(page_text)
    return "\n".join(text_chunks)


def extract_text_from_docx(docx_path: str) -> str:
    """Extract text content from paragraphs and tables of a Word (.docx) document."""
    try:
        import docx
    except ImportError:
        raise ImportError("python-docx is required to parse Word documents. Install via `pip install python-docx`.")

    doc = docx.Document(docx_path)
    text_chunks = []

    # Extract paragraphs
    for para in doc.paragraphs:
        if para.text.strip():
            text_chunks.append(para.text.strip())

    # Extract table cells
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    text_chunks.append(cell_text)

    return "\n".join(text_chunks)


def extract_text_from_txt(txt_path: str) -> str:
    """Extract text from a plain text file."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(txt_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(txt_path, "r", errors="ignore") as f:
        return f.read()


def extract_text_from_file(file_path: str) -> str:
    """Route file by extension to the appropriate text extractor."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    elif ext in [".txt", ".md"]:
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported formats: .pdf, .docx, .txt")


def load_corpus_from_path(source_path: str) -> str:
    """
    Load raw text corpus from either a single file (.pdf, .docx, .txt)
    or a directory containing multiple documents.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source path '{source_path}' does not exist.")

    if os.path.isfile(source_path):
        return extract_text_from_file(source_path)

    # If directory, scan and ingest all supported files
    supported_exts = {".pdf", ".docx", ".doc", ".txt", ".md"}
    combined_texts = []

    for root, _, files in os.walk(source_path):
        for file in sorted(files):
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_exts:
                file_full_path = os.path.join(root, file)
                try:
                    text = extract_text_from_file(file_full_path)
                    if text.strip():
                        combined_texts.append(text)
                except Exception as e:
                    print(f"[Warning] Failed to read {file_full_path}: {e}")

    if not combined_texts:
        raise ValueError(f"No readable documents found in directory '{source_path}'.")

    return "\n\n".join(combined_texts)


def split_into_sentences(text: str, min_words: int = 4, max_words: int = 45) -> List[str]:
    """
    Split text into clean, well-formed grammatical sentences.
    Filters out noise, page headers, numbers, and fragments.
    """
    # Normalize whitespace and linebreaks
    text = re.sub(r"[\r\n]+", " ", text)
    # Strip document headers and page indicators (e.g. Page 1, Meaningful and Meaningless Sentences)
    text = re.sub(r'\bPage\s+\d+\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\bMeaningful and Meaningless Sentences\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()

    # Rule-based sentence segmentation with abbreviation protection
    # Protect common abbreviations
    abbr_map = {
        "e.g.": "eg_placeholder",
        "i.e.": "ie_placeholder",
        "etc.": "etc_placeholder",
        "Dr.": "dr_placeholder",
        "Mr.": "mr_placeholder",
        "Mrs.": "mrs_placeholder",
        "Ms.": "ms_placeholder",
        "Prof.": "prof_placeholder",
        "vs.": "vs_placeholder",
        "Fig.": "fig_placeholder",
        "al.": "al_placeholder",
        "Inc.": "inc_placeholder",
        "Ltd.": "ltd_placeholder"
    }

    for abbr, placeholder in abbr_map.items():
        text = text.replace(abbr, placeholder)

    # Split on sentence terminals followed by space and uppercase/quote
    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'“])', text)

    clean_sentences = []
    for s in raw_sentences:
        # Restore abbreviations
        for abbr, placeholder in abbr_map.items():
            s = s.replace(placeholder, abbr)

        s = s.strip()
        # Remove bullet points, numbers, dashes at the start
        s = re.sub(r"^[\d\.\-\*\•\–\—\)\(\]\[]+\s*", "", s).strip()

        # Validate sentence viability
        words = s.split()
        if min_words <= len(words) <= max_words:
            # Must end with valid punctuation
            if not re.search(r'[.!?]["\'”]?$', s):
                s += "."
            # Must start with a capitalized letter
            if s[0].isalpha() and not s[0].isupper():
                s = s[0].upper() + s[1:]
            clean_sentences.append(s)

    # Deduplicate while preserving order
    seen = set()
    unique_sentences = []
    for s in clean_sentences:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique_sentences.append(s)

    return unique_sentences


# Comprehensive core corpus of high-quality, diverse grammatical patterns
CORE_SENTENCE_CORPUS = [
    # Quantifier & determiner patterns with mental states and attributes
    "Many of the boys have very poor motivation.",
    "Many of the boys have poor motivation.",
    "Most of the students passed the examination with excellent grades.",
    "A few of the children were playing happily in the park.",
    "Several students in the classroom need extra attention from the teacher.",
    "All of the workers completed their assignments on time.",
    "Some of the answers given during the test were completely incorrect.",
    "A large number of young people lack sufficient self confidence.",
    "Many students struggle with difficult mathematical concepts.",
    "Most of the boys have great passion for playing football.",
    "Some of the girls showed wonderful artistic talent in the exhibition.",
    "Many of the candidates lacked proper preparation for the interview.",
    "Few of the committee members attended the annual meeting yesterday.",
    "None of the passengers were injured in the minor traffic accident.",
    "Each of the participants received a certificate of completion.",
    "Both of the brothers work hard to support their family.",

    # Daily actions, food, and activities
    "Yesterday she went to the market with her mother to buy vegetables.",
    "Yesterday she went to the market.",
    "She went to the market yesterday.",
    "The boy is eating an apple.",
    "The young boy is eating a fresh red apple in the garden.",
    "He goes to school by bus every single day.",
    "He goes to school by bus everyday.",
    "She drinks a warm cup of coffee before starting her daily work.",
    "The chef prepared a delicious dinner for all the invited guests.",
    "My older sister loves reading mystery novels before going to bed.",
    "They are playing football in the school playground after class.",
    "The doctor examined the sick patient very carefully in the clinic.",
    "We walked through the quiet forest beside the clear blue lake.",
    "The diligent gardener watered all the flowering plants in the yard.",
    "He returned the lost wallet to its rightful owner at the police station.",
    "The family visited their grandparents during the summer holidays.",
    "She bought a beautiful blue dress for the wedding ceremony.",
    "The children were laughing and running around the water fountain.",
    "He forgot to bring his umbrella on a very rainy afternoon.",
    "There are very beautiful flowers in the garden.",
    "The flowers in the garden are very beautiful.",

    # School, education, and learning
    "The teacher explained the complex scientific lesson with simple examples.",
    "Students should read good books to improve their vocabulary and writing.",
    "The professor gave an inspiring lecture on modern world history.",
    "She completed her master's degree in computer science with top honors.",
    "The university library remains open until late evening on weekdays.",
    "Learning a second language opens up many career opportunities.",
    "The principal praised the students for their outstanding sports performance.",
    "He asked several thoughtful questions during the chemistry laboratory class.",
    "Practicing grammar exercises regularly helps build fluent communication skills.",
    "The research team published their groundbreaking findings in an academic journal.",

    # Technology, science, and modern world
    "Artificial intelligence is rapidly changing how people live and work.",
    "The software engineer fixed several critical bugs in the mobile application.",
    "Computers process vast amounts of complex data in milliseconds.",
    "Renewable solar energy will play a vital role in protecting our planet.",
    "The new smartphone features an advanced high resolution camera system.",
    "Electric vehicles are becoming more popular across the entire country.",
    "The company launched an innovative cloud platform for small businesses.",
    "Scientists discovered a fascinating new species of plant in the rainforest.",
    "Internet connectivity allows people to communicate instantly across the globe.",
    "Data security and privacy protection are essential in the digital era.",

    # Descriptive, environmental, and emotional states
    "There are very colorful and fragrant flowers blooming in the garden.",
    "The sudden heavy rain caused waterlogging along the main road.",
    "The driver slowed down cautiously because the road was wet and slippery.",
    "The sunset painted the evening sky in vibrant shades of pink and gold.",
    "He felt extremely proud when he received the employee of the year award.",
    "She spoke with confidence and clarity during the business presentation.",
    "Fresh morning air and physical exercise are beneficial for overall health.",
    "The old museum in the city center contains priceless historical artifacts.",
    "A gentle cool breeze blew across the sandy beach at twilight.",
    "Traveling to distant places exposes travelers to rich foreign cultures.",
    "Honesty and integrity are the most valuable virtues a person can possess.",
    "The loud thunder shook the windows during the midnight storm.",
    "The photographer captured a breathtaking photograph of the snow covered mountain.",
    "They celebrated their team's hard earned victory with great excitement.",
    "Patience and persistent effort lead to long term success in life."
]


class SentenceCorrupter:
    """
    Generates realistic destructive sentence variations from clean,
    meaningful constructive sentences to create supervised training pairs.
    """

    def __init__(self, seed: Optional[int] = 42):
        if seed is not None:
            random.seed(seed)

    def corrupt(self, sentence: str, style: str = "hybrid") -> str:
        """
        Generate a destructive sentence according to specified strategy.
        Styles: 'telegraphic', 'jumble', 'omission', 'grammar_noise', 'hybrid'
        """
        if style == "telegraphic":
            return self._telegraphic(sentence)
        elif style == "jumble":
            return self._jumble(sentence)
        elif style == "omission":
            return self._omit_words(sentence)
        elif style == "grammar_noise":
            return self._grammar_noise(sentence)
        else:  # hybrid
            return self._hybrid_corrupt(sentence)

    def _strip_punct(self, word: str) -> str:
        return re.sub(r"[^\w\s]", "", word)

    def _telegraphic(self, sentence: str) -> str:
        """
        Simulates telegraphic / keyword-only input (e.g. 'Many of the boys have very poor motivation.'
        -> 'Many boys poor motivation' or 'boys poor motivation many').
        Strips closed-class function words: articles, partitives ('of'), auxiliaries ('have', 'is'),
        intensifiers ('very', 'really'), and converts to clean lowercase keywords.
        """
        droppable = ARTICLES | PREPOSITIONS | AUXILIARY_VERBS | {"very", "really", "quite", "extremely", "a", "an", "the", "of"}
        words = sentence.split()
        retained = []
        for w in words:
            clean = self._strip_punct(w).lower()
            if clean in droppable:
                continue
            if clean:
                retained.append(clean)

        # If too many were dropped, keep first and last content words
        if len(retained) < 2:
            retained = [self._strip_punct(w).lower() for w in words if self._strip_punct(w)]

        # 30% chance to lightly swap order to simulate jumbled keywords
        if len(retained) >= 3 and random.random() < 0.35:
            # Shift first word or swap two words
            if random.random() < 0.5:
                retained = retained[1:] + [retained[0]]
            else:
                retained[0], retained[1] = retained[1], retained[0]

        return " ".join(retained)

    def _jumble(self, sentence: str) -> str:
        """Heavily scrambles the word order to destroy SVO syntax."""
        words = [_w for _w in [self._strip_punct(w).lower() for w in sentence.split()] if _w]
        if len(words) <= 2:
            return " ".join(reversed(words))

        jumbled = words[:]
        for _ in range(5):
            random.shuffle(jumbled)
            if jumbled != words:
                break
        return " ".join(jumbled)

    def _omit_words(self, sentence: str) -> str:
        """Drops essential function words: articles, prepositions, and auxiliaries."""
        words = sentence.split()
        remaining = []
        for w in words:
            clean_w = self._strip_punct(w).lower()
            if (clean_w in ARTICLES or clean_w in PREPOSITIONS or clean_w in AUXILIARY_VERBS or clean_w in {"of", "very"}) and random.random() < 0.70:
                continue
            clean = self._strip_punct(w).lower()
            if clean:
                remaining.append(clean)

        if len(remaining) < 2:
            remaining = [self._strip_punct(w).lower() for w in words if self._strip_punct(w)]

        return " ".join(remaining)

    def _grammar_noise(self, sentence: str) -> str:
        """Introduces tense mismatches, subject-verb agreement breakages, and casing flaws."""
        words = [self._strip_punct(w) for w in sentence.split() if w]
        corrupted = []
        for w in words:
            lw = w.lower()
            if lw == "is":
                corrupted.append("are" if random.random() < 0.5 else "be")
            elif lw == "are":
                corrupted.append("is" if random.random() < 0.5 else "was")
            elif lw == "was":
                corrupted.append("were" if random.random() < 0.5 else "is")
            elif lw == "were":
                corrupted.append("was" if random.random() < 0.5 else "are")
            elif lw == "has":
                corrupted.append("have")
            elif lw == "have":
                corrupted.append("has" if random.random() < 0.5 else "had")
            elif lw == "goes":
                corrupted.append("go")
            elif lw == "went":
                corrupted.append("go")
            elif lw.endswith("ing") and len(lw) > 5 and random.random() < 0.4:
                corrupted.append(lw[:-3])  # running -> run
            else:
                corrupted.append(lw)
        return " ".join(corrupted)

    def _hybrid_corrupt(self, sentence: str) -> str:
        """
        Full destructive simulation:
        Drops function words, swaps and shuffles word sequences, strips punctuation,
        and converts to lower/destructive case.
        """
        words = [self._strip_punct(w).lower() for w in sentence.split() if self._strip_punct(w)]
        if not words:
            return sentence.lower()

        # Step 1: Omission (drop function words)
        retained = []
        for w in words:
            if (w in ARTICLES or w in PREPOSITIONS or w in AUXILIARY_VERBS or w in {"of", "very"}) and random.random() < 0.60:
                continue
            retained.append(w)

        if len(retained) < 2:
            retained = words[:]

        # Step 2: Inversion / Jumbling
        n = len(retained)
        if n >= 3:
            split_idx = random.randint(1, n - 1)
            chunk1, chunk2 = retained[:split_idx], retained[split_idx:]
            if random.random() < 0.55:
                retained = chunk2 + chunk1

            if random.random() < 0.40 and n > 2:
                i, j = random.sample(range(n), 2)
                retained[i], retained[j] = retained[j], retained[i]

        return " ".join(retained)


def create_training_pairs(
    sentences: List[str],
    augmentations_per_sentence: int = 5
) -> List[Tuple[str, str]]:
    """
    Generate multiple (destructive_sentence, constructive_sentence) pairs
    from a collection of clean sentences using diverse corruption strategies.
    """
    corrupter = SentenceCorrupter()
    pairs = []
    styles = ["telegraphic", "hybrid", "jumble", "omission", "grammar_noise"]

    for sent in sentences:
        target = sent.strip()

        # Create diverse destructive variants
        for i in range(augmentations_per_sentence):
            style = styles[i % len(styles)]
            destructive = corrupter.corrupt(target, style=style)
            if destructive.strip() and destructive.lower() != target.lower():
                pairs.append((destructive, target))

    return pairs


def load_all_training_sentences(source_path: Optional[str] = None) -> List[str]:
    """
    Combines extracted sentences from user documents with the comprehensive core corpus,
    ensuring robust grammatical coverage and vocabulary breadth.
    """
    sentences = list(CORE_SENTENCE_CORPUS)
    seen = {s.lower().strip() for s in sentences}

    if source_path and os.path.exists(source_path):
        try:
            doc_text = load_corpus_from_path(source_path)
            doc_sentences = split_into_sentences(doc_text)
            for s in doc_sentences:
                clean_s = s.strip()
                if clean_s.lower() not in seen:
                    seen.add(clean_s.lower())
                    sentences.append(clean_s)
        except Exception as e:
            print(f"[Warning] Could not ingest sentences from {source_path}: {e}")

    return sentences


class SentenceConstructionDataset(Dataset):
    """
    PyTorch Dataset mapping destructive inputs to constructive targets
    for Seq2Seq Transformer fine-tuning.
    """

    def __init__(
        self,
        pairs: List[Tuple[str, str]],
        tokenizer,
        max_source_length: int = 64,
        max_target_length: int = 64,
        prefix: str = "construct a complete, meaningful sentence: "
    ):
        self.pairs = pairs
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
        self.prefix = prefix

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        destructive_input, constructive_target = self.pairs[idx]

        # Add task prompt prefix for T5 models
        input_text = self.prefix + destructive_input

        # Tokenize source
        source_encoding = self.tokenizer(
            input_text,
            max_length=self.max_source_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        # Tokenize target
        target_encoding = self.tokenizer(
            constructive_target,
            max_length=self.max_target_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        labels = target_encoding["input_ids"].squeeze(0)
        # Replace padding token id with -100 so loss ignores it
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            "input_ids": source_encoding["input_ids"].squeeze(0),
            "attention_mask": source_encoding["attention_mask"].squeeze(0),
            "labels": labels
        }
