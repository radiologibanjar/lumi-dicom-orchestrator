# Lumi DICOM Orchestrator — Dockerfile
# Copyright © 2026 Lumi DICOM. All rights reserved.

FROM python:3.12-slim

# Labels
LABEL org.opencontainers.image.title="Lumi DICOM Orchestrator"
LABEL org.opencontainers.image.description="DICOM Modality Worklist orchestrator for radiology workflows"
LABEL org.opencontainers.image.vendor="Lumi DICOM"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LUMI_DICOM_DATABASE__PATH=/data/worklist.db \
    LUMI_DICOM_API__PORT=8765 \
    LUMI_DICOM_MWL_SCP__PORT=11112

WORKDIR /app

# Install dependencies
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY config/ ./config/
RUN pip install --no-cache-dir -e .

# Data volume
RUN mkdir -p /data
VOLUME ["/data"]

# Expose ports
# 8765 — Inbound API (HTTP)
# 11112 — DICOM MWL SCP
EXPOSE 8765 11112

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')" || exit 1

# Entry point
ENTRYPOINT ["lumi-dicom"]
CMD ["start", "--config", "config/default.yaml"]
