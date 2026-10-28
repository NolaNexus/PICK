FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RPY2_CFFI_MODE=ABI

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        r-base \
        r-cran-mass \
        r-cran-survival \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-r.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -r requirements-r.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
