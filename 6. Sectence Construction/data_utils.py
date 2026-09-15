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
        Styles: 'jumble', 'omission', 'grammar_noise', 'hybrid'
        """
        if style == "jumble":
            return self._jumble(sentence)
        elif style == "omission":
            return self._omit_words(sentence)
        elif style == "grammar_noise":
            return self._grammar_noise(sentence)
        else:  # hybrid
            return self._hybrid_corrupt(sentence)

    def _strip_punct(self, word: str) -> str:
        return re.sub(r"[^\w\s]", "", word)

    def _jumble(self, sentence: str) -> str:
        """Heavily scrambles the word order to destroy SVO syntax."""
        words = [_w for _w in [self._strip_punct(w).lower() for w in sentence.split()] if _w]
        if len(words) <= 2:
            return " ".join(reversed(words))

        jumbled = words[:]
        # Ensure it actually gets shuffled differently from original
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
            # 65% chance to drop articles, prepositions, or auxiliaries
            if (clean_w in ARTICLES or clean_w in PREPOSITIONS or clean_w in AUXILIARY_VERBS) and random.random() < 0.65:
                continue
            remaining.append(self._strip_punct(w).lower())

        if len(remaining) < 2:
            remaining = [self._strip_punct(w).lower() for w in words]

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
                corrupted.append("has")
            elif lw.endswith("ing") and len(lw) > 5 and random.random() < 0.3:
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

        # Step 1: Omission (drop some function words)
        retained = []
        for w in words:
            if (w in ARTICLES or w in PREPOSITIONS or w in AUXILIARY_VERBS) and random.random() < 0.55:
                continue
            retained.append(w)

        if len(retained) < 2:
            retained = words[:]

        # Step 2: Inversion / Jumbling
        n = len(retained)
        if n >= 3:
            # Cut into chunks and swap or partial shuffle
            split_idx = random.randint(1, n - 1)
            chunk1, chunk2 = retained[:split_idx], retained[split_idx:]
            # 60% chance to swap chunks
            if random.random() < 0.60:
                retained = chunk2 + chunk1

            # 40% chance of random local swap
            if random.random() < 0.40 and n > 2:
                i, j = random.sample(range(n), 2)
                retained[i], retained[j] = retained[j], retained[i]

        return " ".join(retained)


def create_training_pairs(
    sentences: List[str],
    augmentations_per_sentence: int = 3
) -> List[Tuple[str, str]]:
    """
    Generate multiple (destructive_sentence, constructive_sentence) pairs
    from a collection of clean sentences.
    """
    corrupter = SentenceCorrupter()
    pairs = []
    styles = ["hybrid", "jumble", "omission", "grammar_noise"]

    for sent in sentences:
        # Original clean sentence is the target
        target = sent.strip()

        # Create diverse destructive variants
        for i in range(augmentations_per_sentence):
            style = styles[i % len(styles)]
            destructive = corrupter.corrupt(target, style=style)
            # Ensure destructive is not identical to target
            if destructive.strip() and destructive.lower() != target.lower():
                pairs.append((destructive, target))

    return pairs


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
        prefix: str = "construct meaningful sentence: "
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
