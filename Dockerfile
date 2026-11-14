# V7.13: real DOCX/PPTX -> PDF rendering on the SAME Render web service.
# Select Docker runtime for the existing Render service (see README_V7_13.md).
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer libreoffice-impress fonts-noto-core fonts-noto-ui-core fonts-liberation fontconfig \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-tam tesseract-ocr-ara tesseract-ocr-sin \
    ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . .
# V13 legacy fonts: optional user-supplied, legally licensed .ttf/.otf files.
# No proprietary font files are included in this patch.
RUN mkdir -p /usr/local/share/fonts/student-office && \
    if [ -d /app/office_fonts ]; then \
      find /app/office_fonts -maxdepth 1 -type f \( -iname '*.ttf' -o -iname '*.otf' \) \
        -exec cp '{}' /usr/local/share/fonts/student-office/ \; ; \
    fi && fc-cache -f
# Retain the Text -> PDF Unicode font preparation from V7.11.
RUN if [ -f INSTALL_TEXT_PDF_FONTS.py ]; then python INSTALL_TEXT_PDF_FONTS.py; fi
RUN useradd --create-home --uid 10001 bot && chown -R bot:bot /app
USER bot
ENV SAL_USE_VCLPLUGIN=svp
CMD ["sh", "-c", "exec gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads ${BOT_WEB_THREADS:-8} --timeout 180"]
