FROM python:3.11-slim

LABEL maintainer="devops-bootcamp"
LABEL app="bookvault"

RUN groupadd -r bookvault && useradd -r -g bookvault -s /bin/false bookvault

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip wheel "jaraco.context>=6.1.0"


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .

RUN chown -R bookvault:bookvault /app

USER bookvault

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "wsgi:app"]
