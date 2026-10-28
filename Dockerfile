FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# R is deliberately not installed. The statistical bridge in
# app/services/r_stats.py needs rpy2, which has no binary wheel and has to be
# compiled against a local R install. That is being rebuilt together with the
# calculators; until then the API uses the pure-Python approximations.
# To enable it, install R and run `pip install -r requirements-r.txt`.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
