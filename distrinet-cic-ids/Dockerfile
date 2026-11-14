# Ung dung phat hien nguy co an ninh mang - chay bang Docker
# Build:  docker build -t ids-app .
# Chay:   docker run --rm -p 8501:8501 ids-app      roi mo http://localhost:8501
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    IDS_DOCKER=1 \
    MPLCONFIGDIR=/tmp/matplotlib

# libgomp1: XGBoost can de chay song song; curl: de Docker kiem tra ung dung con song
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cai thu vien truoc (lop nay duoc dung lai neu chi sua code -> build lai nhanh)
COPY requirements-docker.txt .
RUN pip install -r requirements-docker.txt

# Chi chep nhung gi ung dung can: code, mo hinh da huan luyen, file mau, cau hinh giao dien
COPY .streamlit/config.toml .streamlit/config.toml
COPY src/ids_pipeline.py src/ids_pipeline.py
COPY app/ app/
COPY models/final_model.joblib models/feature_cols.json models/test_lock.json models/
COPY data/samples/ data/samples/

# Khong chay bang quyen root
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fs http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
