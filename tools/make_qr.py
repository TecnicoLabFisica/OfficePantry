#!/usr/bin/env python3
"""Generate the printable QR sticker for the Office Pantry page.

The QR holds nothing but the URL. That is deliberate: the sticker stays valid
no matter how the site changes, and reprinting is only ever needed if the
address itself moves.

    python tools/make_qr.py --url https://tecnicolabfisica.github.io/OfficePantry/
"""

import argparse
import pathlib
import sys

DEFAULT_URL = "https://tecnicolabfisica.github.io/OfficePantry/"
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "qr"


def build(url: str, out_dir: pathlib.Path, label: str) -> list[pathlib.Path]:
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError:
        sys.exit("qrcode is not installed. Run:  pip install 'qrcode[pil]'")

    # High error correction: a sticker on an office wall picks up scuffs, and
    # this level still scans with roughly a third of the code obscured.
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,
                       box_size=12, border=3)
    qr.add_data(url)
    qr.make(fit=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    png_path = out_dir / "office-pantry-qr.png"
    qr.make_image(fill_color="black", back_color="white").save(png_path)
    written.append(png_path)

    svg_path = out_dir / "office-pantry-qr.svg"
    qr.make_image(image_factory=SvgPathImage).save(svg_path)
    written.append(svg_path)

    # A print-ready sheet, so the sticker goes up with a caption rather than a
    # bare square nobody recognises.
    html_path = out_dir / "print.html"
    html_path.write_text(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Office Pantry — QR</title>
<style>
  @page {{ margin: 18mm; }}
  body {{ font: 16px system-ui, sans-serif; text-align: center;
         color: #2a2320; margin: 0; padding: 12mm; }}
  h1 {{ font-size: 30px; margin: 0 0 4px; }}
  p  {{ color: #6d6259; margin: 0 0 18px; }}
  img {{ width: 78mm; height: 78mm; }}
  .url {{ font-size: 12px; color: #6d6259; margin-top: 14px; word-break: break-all; }}
</style></head>
<body>
  <h1>🥨 {label}</h1>
  <p>Scan to suggest snacks and see the money</p>
  <img src="office-pantry-qr.png" alt="QR code for {label}">
  <p class="url">{url}</p>
</body></html>
""")
    written.append(html_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=DEFAULT_URL, help=f"target URL (default: {DEFAULT_URL})")
    parser.add_argument("--out", type=pathlib.Path, default=OUT_DIR, help="output directory")
    parser.add_argument("--label", default="Office Pantry", help="caption on the print sheet")
    args = parser.parse_args()

    for path in build(args.url, args.out, args.label):
        print(f"wrote {path}")
    print("\nOpen qr/print.html and print it, or send qr/office-pantry-qr.png to a sticker service.")


if __name__ == "__main__":
    main()
