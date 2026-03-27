#!/usr/bin/env python3
"""Generate images using Google GenAI (Imagen).

Usage:
    generate.py "a photo of a cat" [--output ./images] [--model gemini-2.0-flash-exp]
    generate.py "make it greener" --input previous.png  # edit mode
"""
import argparse
import base64
import io
import os
import sys
from datetime import datetime
from pathlib import Path

from google import genai
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description="Generate images using Google GenAI")
    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument("--input", "-i", help="Input image for editing (enables edit mode)")
    parser.add_argument("--output", "-o", default="./images", help="Output directory")
    parser.add_argument(
        "--model", "-m",
        default="gemini-2.5-flash-image",
        help="Model: gemini-2.5-flash-image (default), gemini-3-pro-image-preview, imagen-4.0-generate-preview-06-06"
    )
    args = parser.parse_args()

    # Initialize client (uses GOOGLE_API_KEY or GEMINI_API_KEY from env)
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Build content parts
    parts = [{"text": args.prompt}]

    # If input image provided, add it (edit mode)
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input image not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        with open(input_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        # Determine mime type from extension
        suffix = input_path.suffix.lower()
        mime_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(
            suffix.lstrip("."), "image/png"
        )
        parts.append({"inline_data": {"data": image_data, "mime_type": mime_type}})

    # Make the API call
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=[{"role": "user", "parts": parts}],
        )
    except Exception as e:
        print(f"Error calling API: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract image from response
    image_bytes = None
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                data = part.inline_data.data
                # Data might be raw bytes or base64-encoded string
                if isinstance(data, bytes):
                    image_bytes = data
                elif isinstance(data, str):
                    image_bytes = base64.b64decode(data)
                break

    if not image_bytes:
        print("Error: No image data in response", file=sys.stderr)
        sys.exit(1)

    # Save the image (re-save via PIL to strip C2PA metadata that breaks Preview)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"imagen-{timestamp}.png"

    # Handle filename collision
    counter = 1
    while output_path.exists():
        output_path = output_dir / f"imagen-{timestamp}-{counter}.png"
        counter += 1

    # Re-save through PIL to strip Google's C2PA provenance metadata
    # (Preview.app can't handle non-standard PNG chunks)
    img = Image.open(io.BytesIO(image_bytes))
    img.save(output_path)
    print(output_path)


if __name__ == "__main__":
    main()
