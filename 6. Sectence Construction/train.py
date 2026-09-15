"""
train.py
--------
Train a Sequence-to-Sequence Transformer model to construct meaningful,
fluent sentences from destructive / corrupted sentence inputs.

Dataset source: Normal PDF (.pdf), Word (.docx), or plain text (.txt) files.

Usage:
  python train.py --data_path ./sample_dataset.docx --epochs 3 --batch_size 8
"""

import os
import sys
import argparse
import random
import time
from typing import List, Tuple

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import torch
from torch.utils.data import DataLoader, random_split
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    get_linear_schedule_with_warmup
)
from tqdm import tqdm

from data_utils import (
    load_corpus_from_path,
    split_into_sentences,
    create_training_pairs,
    SentenceConstructionDataset,
    load_all_training_sentences,
    CORE_SENTENCE_CORPUS
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train a Sentence Construction Seq2Seq Model from a PDF or Word document."
    )
    parser.add_argument(
        "--data_path",
        type=str,
        default=None,
        help="Path to your PDF file (.pdf), Word document (.docx), or text file. If omitted, auto-discovers PDF in current directory."
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="google/flan-t5-small",
        help="Pretrained Seq2Seq base model name (e.g. 'google/flan-t5-small', 'google/flan-t5-base')."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./saved_model",
        help="Directory path to save the trained model checkpoint and tokenizer."
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="Number of training epochs."
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=16,
        help="Training batch size per device."
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=3e-4,
        help="Learning rate for AdamW optimizer."
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=64,
        help="Maximum sequence token length for inputs and outputs."
    )
    parser.add_argument(
        "--augmentations_per_sentence",
        type=int,
        default=5,
        help="Number of destructive training variants to synthesize per clean sentence."
    )
    parser.add_argument(
        "--val_split",
        type=float,
        default=0.1,
        help="Proportion of training pairs reserved for validation."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility."
    )
    return parser.parse_args()


def set_seed(seed: int):
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def evaluate(model, val_loader, device):
    """Compute cross-entropy loss over validation dataset."""
    model.eval()
    total_val_loss = 0.0
    num_batches = 0

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            loss = outputs.loss
            total_val_loss += loss.item()
            num_batches += 1

    model.train()
    return total_val_loss / max(num_batches, 1)


def train():
    args = parse_args()
    set_seed(args.seed)

    # Auto-detect PDF file if not specified
    if not args.data_path:
        pdf_candidates = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
        if pdf_candidates:
            args.data_path = pdf_candidates[0]
            print(f"[*] Auto-detected PDF dataset in directory: '{args.data_path}'")
        else:
            docx_candidates = [f for f in os.listdir(".") if f.lower().endswith(".docx")]
            if docx_candidates:
                args.data_path = docx_candidates[0]
                print(f"[*] Auto-detected Word dataset in directory: '{args.data_path}'")

    print("=" * 70)
    print(" [*] NATIVOX: SENTENCE CONSTRUCTION MODEL TRAINING")
    print("=" * 70)
    print(f" - Source Dataset Path : {args.data_path}")
    print(f" - Base Model          : {args.model_name}")
    print(f" - Output Directory    : {args.output_dir}")
    print(f" - Target Epochs       : {args.epochs}")
    print(f" - Batch Size          : {args.batch_size}")
    print(f" - Learning Rate       : {args.lr}")
    print(f" - Max Sequence Length : {args.max_length}")
    print("=" * 70)

    # 1. Ingest document and combine with core linguistic corpus
    print(f"\n[1/5] Ingesting sentences from document and core grammatical corpus...")
    sentences = load_all_training_sentences(args.data_path)
    print(f"      Loaded {len(sentences):,} clean grammatical sentences.")

    if len(sentences) < 2:
        print("[Error] Not enough sentences available to train.")
        sys.exit(1)

    # 2. Generate destructive pairs
    print(f"\n[2/5] Synthesizing destructive sentence pairs (factor={args.augmentations_per_sentence}x)...")
    training_pairs = create_training_pairs(
        sentences,
        augmentations_per_sentence=args.augmentations_per_sentence
    )
    print(f"      Generated {len(training_pairs):,} (Destructive Input -> Constructive Target) pairs.")

    print("\n      Sample Generated Pairs:")
    for idx, (dest, constr) in enumerate(training_pairs[:4], 1):
        print(f"      [{idx}] DESTRUCTIVE  : {dest}")
        print(f"          CONSTRUCTIVE : {constr}")

    # 3. Initialize Tokenizer and Dataset
    print(f"\n[3/5] Loading tokenizer & base model '{args.model_name}'...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model_name)

    dataset = SentenceConstructionDataset(
        pairs=training_pairs,
        tokenizer=tokenizer,
        max_source_length=args.max_length,
        max_target_length=args.max_length,
        prefix="construct a complete, meaningful sentence: "
    )

    # Train/Validation split
    val_size = max(1, int(len(dataset) * args.val_split))
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        drop_last=False
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False
    )

    print(f"      Training samples: {len(train_dataset)} | Validation samples: {len(val_dataset)}")

    # Device setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"      Training Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    model.to(device)

    # Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total_steps = len(train_loader) * args.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * 0.1),
        num_training_steps=total_steps
    )

    # 5. Training Loop
    print("\n[5/5] Starting fine-tuning loop...")
    best_val_loss = float("inf")
    start_time = time.time()

    model.train()
    for epoch in range(1, args.epochs + 1):
        epoch_loss = 0.0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs}", unit="batch")

        for step, batch in enumerate(pbar):
            optimizer.zero_grad()

            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            loss = outputs.loss

            if torch.isnan(loss) or torch.isinf(loss):
                continue

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            epoch_loss += loss.item()
            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        avg_train_loss = epoch_loss / max(len(train_loader), 1)
        avg_val_loss = evaluate(model, val_loader, device)

        print(f"  --> Epoch {epoch:02d} Complete | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")

        # Save best model
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            os.makedirs(args.output_dir, exist_ok=True)
            model.save_pretrained(args.output_dir)
            tokenizer.save_pretrained(args.output_dir)
            print(f"      [OK] Checkpoint saved to {args.output_dir} (Val Loss: {best_val_loss:.4f})")

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f" [SUCCESS] TRAINING COMPLETE in {elapsed:.1f}s")
    print(f" Best Validation Loss: {best_val_loss:.4f}")
    print(f" Saved Model Directory: {os.path.abspath(args.output_dir)}")
    print("=" * 70)

    # Demonstration of inference on a few sample destructive sentences
    print("\n[*] Quick Validation Inference Test:")
    sample_destructive = [
        "Many boys poor motivation",
        "market went yesterday she to the",
        "eating apple boy an is",
        "he go school bus everyday by",
        "artificial intelligence rapidly world changing is"
    ]
    model.eval()
    prefix = "construct a complete, meaningful sentence: "

    for sent in sample_destructive:
        input_ids = tokenizer(
            prefix + sent,
            return_tensors="pt",
            truncation=True,
            max_length=args.max_length
        ).input_ids.to(device)

        with torch.no_grad():
            outputs = model.generate(
                input_ids,
                max_length=args.max_length,
                num_beams=4,
                no_repeat_ngram_size=3,
                length_penalty=1.2,
                early_stopping=True
            )
        constructed = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"  - Destructive : \"{sent}\"")
        print(f"    Constructive: \"{constructed}\"")
    print("=" * 70)


if __name__ == "__main__":
    train()
