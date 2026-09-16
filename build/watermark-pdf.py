#!/usr/bin/env python3
"""Stamp Baker 1031 contact details onto sponsor PDFs.

A discreet band across the foot of every page — firm name, invest@baker1031.com, (310) 896-4227 —
backed in white so it sits below the sponsor's own text rather than over it. The page content is
untouched; nothing is removed, reworded or re-laid-out.

    python3 build/watermark-pdf.py IN.pdf OUT.pdf
    python3 build/watermark-pdf.py --in-dir sponsor-pdfs --out-dir stamped
    python3 build/watermark-pdf.py IN.pdf OUT.pdf --first-page-only
    python3 build/watermark-pdf.py IN.pdf OUT.pdf --line "Provided by Baker 1031 Investments"

BEFORE USING THIS: a sponsor's PDF is their copyrighted work, usually carrying a compliance version
code (V-23-78, IU-GCC566, 20240911-3851200-...) that ties the approved wording to that exact file.
Stamping changes the file. Get the sponsor's written okay for co-branded or rep-stamped distribution
first, and have the result reviewed the way any retail communication would be. See
build/sponsor-materials-README.md.
"""
import argparse
import io
import os
import sys

FIRM = 'Baker 1031 Investments'
EMAIL = 'invest@baker1031.com'
PHONE = '(310) 896-4227'
BLUE = (0 / 255, 84 / 255, 153 / 255)


def stamp_layer(width, height, line):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    band = 26
    c.setFillColorRGB(1, 1, 1)
    c.setFillAlpha(0.88)
    c.rect(0, 0, width, band, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.setStrokeColorRGB(*BLUE)
    c.setLineWidth(0.6)
    c.line(0, band, width, band)
    c.setFillColorRGB(*BLUE)
    c.setFont('Helvetica-Bold', 7.5)
    c.drawString(28, band / 2 - 2.6, FIRM)
    c.setFillColorRGB(0.29, 0.33, 0.38)
    c.setFont('Helvetica', 7.5)
    c.drawRightString(width - 28, band / 2 - 2.6, f'{EMAIL}   |   {PHONE}')
    if line:
        c.setFont('Helvetica-Oblique', 6.5)
        c.drawCentredString(width / 2, band / 2 - 2.4, line)
    c.save()
    buf.seek(0)
    return buf


def stamp(src, dst, first_page_only=False, line=''):
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(src)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if not first_page_only or i == 0:
            box = page.mediabox
            w, h = float(box.width), float(box.height)
            layer = PdfReader(stamp_layer(w, h, line)).pages[0]
            page.merge_page(layer)
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata({k: v for k, v in reader.metadata.items() if isinstance(v, str)})
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'wb') as fh:
        writer.write(fh)
    return len(reader.pages)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', nargs='?')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--in-dir')
    ap.add_argument('--out-dir')
    ap.add_argument('--first-page-only', action='store_true')
    ap.add_argument('--line', default='')
    a = ap.parse_args()

    if a.in_dir:
        out = a.out_dir or (a.in_dir.rstrip('/') + '-stamped')
        n = 0
        for name in sorted(os.listdir(a.in_dir)):
            if not name.lower().endswith('.pdf'):
                continue
            pages = stamp(os.path.join(a.in_dir, name), os.path.join(out, name), a.first_page_only, a.line)
            print(f'  {name}  ({pages} pages)')
            n += 1
        print(f'{n} PDFs stamped into {out}/')
    elif a.src and a.dst:
        print(f'{stamp(a.src, a.dst, a.first_page_only, a.line)} pages stamped -> {a.dst}')
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
