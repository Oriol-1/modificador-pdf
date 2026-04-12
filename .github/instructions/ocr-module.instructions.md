---
description: "Use when working on the OCR module: image preprocessing with OpenCV, Tesseract integration, PDF searchable layer creation, or OCR UI components."
applyTo: "core/ocr/**/*.py"
---
# OCR Module Guidelines

## Architecture
```
core/ocr/
├── __init__.py
├── image_preprocessor.py   # OpenCV pipeline: deskew, denoise, binarize, enhance
├── ocr_engine.py            # Abstract OCREngine interface
├── tesseract_engine.py      # Tesseract 5 implementation
└── pdf_ocr_layer.py         # Create invisible text layer on scanned PDFs
```

## Pipeline Flow
1. **Detect** scanned PDF → `pdf_handler.is_scanned_pdf()`
2. **Extract** page as image → `page.get_pixmap(dpi=300)`
3. **Preprocess** image → `ImagePreprocessor.process(image)`
   - Deskew (Hough lines)
   - Denoise (bilateral filter)
   - Binarize (adaptive Otsu)
   - Enhance contrast (CLAHE)
4. **OCR** → `TesseractEngine.recognize(image, lang="spa+eng")`
5. **Map** results to `TextSpanMetrics` from `core.text_engine.text_span`
6. **Overlay** invisible text → `page.insert_text(..., render_mode=3)`

## Dependencies
```python
import cv2                    # opencv-python-headless
import numpy as np
import pytesseract            # pytesseract (requires Tesseract 5 binary)
```

## Key Patterns
- Abstract base class `OCREngine` for swappable backends (Tesseract, PaddleOCR, etc.)
- Output format: list of `OCRResult(text, bbox, confidence, lang)`
- All preprocessing steps are optional and configurable
- Progress callback: `on_progress(page_num: int, total_pages: int)`
