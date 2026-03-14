"""
DiaIntel — Model Downloader
Downloads and caches all required ML models for the NLP pipeline.

Models:
- BioBERT (dmis-lab/biobert-base-cased-v1.2) — batch AE extraction
- DistilBERT (distilbert-base-uncased) — real-time Live Analyzer
- RoBERTa (cardiffnlp/twitter-roberta-base-sentiment) — sentiment analysis
- BART (facebook/bart-large-mnli) — zero-shot misinformation detection

Usage:
    python scripts/download_models.py

All models are saved to MODEL_CACHE_DIR (default: /models).
If a model already exists in the cache directory, it is skipped.
"""

import os
import sys

# CRITICAL: Set before any HuggingFace import
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification
from transformers import AutoModelForTokenClassification
from tqdm import tqdm


# Model registry: (name, model_id, model_class)
MODELS = [
    {
        "name": "BioBERT (Batch AE Extraction)",
        "model_id": "dmis-lab/biobert-base-cased-v1.2",
        "env_key": "BIOBERT_MODEL",
        "model_class": AutoModel,
    },
    {
        "name": "DistilBERT (Real-time Live Analyzer)",
        "model_id": "distilbert-base-uncased",
        "env_key": "DISTILBERT_MODEL",
        "model_class": AutoModel,
    },
    {
        "name": "RoBERTa (Sentiment Analysis)",
        "model_id": "cardiffnlp/twitter-roberta-base-sentiment",
        "env_key": "ROBERTA_MODEL",
        "model_class": AutoModelForSequenceClassification,
    },
    {
        "name": "BART-MNLI (Misinformation Detection)",
        "model_id": "facebook/bart-large-mnli",
        "env_key": "BART_MODEL",
        "model_class": AutoModelForSequenceClassification,
    },
]


def get_cache_dir() -> str:
    """Get the model cache directory from environment or default."""
    return os.environ.get("MODEL_CACHE_DIR", "/models")


def model_exists(cache_dir: str, model_id: str) -> bool:
    """Check if a model has already been downloaded."""
    # Models are saved in subdirectories based on their name
    safe_name = model_id.replace("/", "--")
    model_path = os.path.join(cache_dir, safe_name)
    return os.path.exists(model_path) and len(os.listdir(model_path)) > 0


def download_model(model_info: dict, cache_dir: str) -> bool:
    """Download a single model and its tokenizer."""
    model_id = model_info["model_id"]
    model_class = model_info["model_class"]
    safe_name = model_id.replace("/", "--")
    save_path = os.path.join(cache_dir, safe_name)

    if model_exists(cache_dir, model_id):
        print(f"  ✓ Already cached at {save_path}")
        return True

    try:
        print(f"  Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        tokenizer.save_pretrained(save_path)

        print(f"  Downloading model weights...")
        model = model_class.from_pretrained(model_id)
        model.save_pretrained(save_path)

        print(f"  ✓ Saved to {save_path}")
        return True

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def main():
    """Download all required models."""
    cache_dir = get_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)

    print("=" * 60)
    print("DiaIntel — Model Downloader")
    print("=" * 60)
    print(f"\nCache directory: {cache_dir}")
    print(f"Models to check: {len(MODELS)}\n")

    results = []
    for i, model_info in enumerate(MODELS, 1):
        print(f"\n[{i}/{len(MODELS)}] {model_info['name']}")
        print(f"  Model ID: {model_info['model_id']}")
        success = download_model(model_info, cache_dir)
        results.append((model_info["name"], success))

    # Print summary
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    for name, success in results:
        status = "✓ Ready" if success else "✗ Failed"
        print(f"  {status} — {name}")

    failed = [r for r in results if not r[1]]
    if failed:
        print(f"\n⚠ {len(failed)} model(s) failed to download.")
        print("  Please check your internet connection and try again.")
        sys.exit(1)
    else:
        print(f"\n✓ All {len(results)} models are ready!")
        print("\nNext steps:")
        print("  1. Place your .zst files in backend/data/raw/")
        print("  2. Run: docker compose up")
        print("  3. Open http://localhost:5173 in your browser")


if __name__ == "__main__":
    main()
