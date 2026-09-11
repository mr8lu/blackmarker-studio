"""Download Google Gemma 4 E4B GGUF model weights for air-gapped on-device deployment."""

import argparse
import sys
from pathlib import Path
from urllib.request import urlretrieve
from redact_gov.config import settings


def download_model(repo_id: str, filename: str, target_dir: Path) -> Path:
    """Download GGUF model weights from Hugging Face."""
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename

    if target_path.is_file():
        print(f"Model already exists at: {target_path}")
        return target_path

    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    print(f"Downloading on-device Google Gemma 4 E4B weights from:\n  {url}")
    print(f"Destination:\n  {target_path}")

    def progress_callback(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, downloaded * 100.0 / total_size)
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\rProgress: {percent:.1f}% ({mb:.1f} MB / {total_mb:.1f} MB)")
            sys.stdout.flush()

    try:
        urlretrieve(url, target_path, reporthook=progress_callback)
        print("\nDownload complete.")
        return target_path
    except Exception as e:
        print(f"\nFailed to download weights: {e}")
        if target_path.exists():
            target_path.unlink()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download Google Gemma 4 E4B weights for RedactGov")
    parser.add_argument("--repo", default=settings.GEMMA_MODEL_NAME, help="HuggingFace repository ID")
    parser.add_argument("--file", default=settings.GEMMA_DEFAULT_GGUF_FILE, help="GGUF filename")
    parser.add_argument("--outdir", default=str(settings.MODELS_DIR), help="Output directory")

    args = parser.parse_args()
    download_model(args.repo, args.file, Path(args.outdir))


if __name__ == "__main__":
    main()
