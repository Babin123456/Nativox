"""
construct.py
------------
Inference and testing tool for Sentence Construction.
Takes a destructive sentence (e.g. jumbled words, broken grammar, omitted function words)
and constructs a clean, grammatically fluent, meaningful sentence.

Modes:
  1. Interactive CLI (Default): User inputs destructive sentences in real time.
  2. Single Sentence Mode: Pass sentence via `--sentence "your destructive text"`
  3. Batch File Mode: Process a text file with one sentence per line via `--batch_file input.txt`

Usage:
  python construct.py
  python construct.py --sentence "yesterday went she market to the"
  python construct.py --batch_file test_cases.txt
"""

import os
import sys
import argparse
import time
import re

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


class SentenceConstructor:
    """
    Sentence Construction Engine powered by fine-tuned Seq2Seq Transformer.
    """

    def __init__(self, model_path: str = "./saved_model", base_fallback: str = "t5-small"):
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Determine model path
        if os.path.exists(model_path) and os.path.exists(os.path.join(model_path, "config.json")):
            load_target = model_path
            print(f"[OK] Loading fine-tuned model checkpoint from: {os.path.abspath(load_target)}")
        else:
            print(f"[!] Fine-tuned checkpoint not found at '{model_path}'.")
            print(f"    Falling back to base model '{base_fallback}' with zero-shot instruction prompt.")
            print(f"    Tip: Run `python train.py` first to fine-tune on your document dataset!")
            load_target = base_fallback

        print(f"[*] Initializing model on device: {self.device}")
        self.tokenizer = AutoTokenizer.from_pretrained(load_target)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(load_target)
        self.model.to(self.device)
        self.model.eval()

        self.prefix = "construct meaningful sentence: "

    def construct(
        self,
        destructive_sentence: str,
        num_beams: int = 4,
        max_length: int = 64
    ) -> str:
        """
        Reconstruct a destructive sentence into a grammatically coherent, meaningful sentence.
        """
        cleaned_input = destructive_sentence.strip()
        if not cleaned_input:
            return ""

        prompt = self.prefix + cleaned_input
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=max_length
        ).to(self.device)

        with torch.no_grad():
            output_tokens = self.model.generate(
                **inputs,
                max_length=max_length,
                num_beams=num_beams,
                no_repeat_ngram_size=3,
                length_penalty=1.0,
                early_stopping=True
            )

        constructed = self.tokenizer.decode(output_tokens[0], skip_special_tokens=True).strip()

        # Post-processing: capital start and terminal punctuation
        if constructed:
            # Capitalize first character
            if constructed[0].isalpha() and not constructed[0].isupper():
                constructed = constructed[0].upper() + constructed[1:]
            # Ensure ending punctuation
            if not re.search(r'[.!?]["\'”]?$', constructed):
                constructed += "."

        return constructed


def run_interactive(constructor: SentenceConstructor, num_beams: int = 4, max_length: int = 64):
    """Interactive command-line loop for testing arbitrary destructive sentences."""
    print("\n" + "=" * 75)
    print(" [*] NATIVOX: INTERACTIVE SENTENCE CONSTRUCTION TESTING")
    print("=" * 75)
    print(" Enter any destructive sentence (e.g., scrambled words, broken grammar).")
    print(" Type 'exit', 'quit', or 'q' to stop.")
    print("=" * 75 + "\n")

    examples = [
        "market went yesterday she to the",
        "eating apple boy an is",
        "artificial intelligence changing world rapidly is",
        "he go school bus everyday by",
        "beautiful very flowers garden the in are"
    ]

    print("[*] Example destructive sentences you can test:")
    for ex in examples:
        print(f"   - {ex}")
    print()

    while True:
        try:
            user_input = input("Destructive Input > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        t0 = time.time()
        result = constructor.construct(user_input, num_beams=num_beams, max_length=max_length)
        latency_ms = (time.time() - t0) * 1000

        print(f"\n Constructive Output > {result}")
        print(f" [Latency: {latency_ms:.1f}ms | Beams: {num_beams}]\n")
        print("-" * 75)


def run_single(constructor: SentenceConstructor, sentence: str, num_beams: int = 4, max_length: int = 64):
    """Run inference on a single command-line input."""
    t0 = time.time()
    result = constructor.construct(sentence, num_beams=num_beams, max_length=max_length)
    latency_ms = (time.time() - t0) * 1000

    print("\n" + "=" * 70)
    print(" [*] SENTENCE CONSTRUCTION RESULT")
    print("=" * 70)
    print(f" - DESTRUCTIVE INPUT   : {sentence}")
    print(f" - CONSTRUCTIVE OUTPUT : {result}")
    print(f" - INFERENCE TIME      : {latency_ms:.1f} ms")
    print("=" * 70)


def run_batch(constructor: SentenceConstructor, file_path: str, num_beams: int = 4, max_length: int = 64):
    """Run inference over a batch of destructive sentences from a text file."""
    if not os.path.exists(file_path):
        print(f"[Error] Batch file '{file_path}' not found.")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    print("\n" + "=" * 80)
    print(f" [*] BATCH SENTENCE CONSTRUCTION ({len(lines)} sentences)")
    print("=" * 80)

    for idx, line in enumerate(lines, 1):
        result = constructor.construct(line, num_beams=num_beams, max_length=max_length)
        print(f"[{idx:02d}] Destructive  : {line}")
        print(f"     Constructive : {result}")
        print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description="Nativox Sentence Construction Testing & Inference Tool")
    parser.add_argument(
        "--model_path",
        type=str,
        default="./saved_model",
        help="Path to the trained model directory (default: ./saved_model)"
    )
    parser.add_argument(
        "--sentence", "-s",
        type=str,
        default=None,
        help="Single destructive sentence to reconstruct."
    )
    parser.add_argument(
        "--batch_file", "-f",
        type=str,
        default=None,
        help="Path to a text file containing destructive sentences (one per line)."
    )
    parser.add_argument(
        "--beams",
        type=int,
        default=4,
        help="Number of beams for beam search decoding (default: 4)."
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=64,
        help="Maximum generated sequence length (default: 64)."
    )

    args = parser.parse_args()

    constructor = SentenceConstructor(model_path=args.model_path)

    if args.sentence:
        run_single(constructor, args.sentence, num_beams=args.beams, max_length=args.max_length)
    elif args.batch_file:
        run_batch(constructor, args.batch_file, num_beams=args.beams, max_length=args.max_length)
    else:
        run_interactive(constructor, num_beams=args.beams, max_length=args.max_length)


if __name__ == "__main__":
    main()
