# Runs the full app (backend + frontend) anywhere Docker runs:
#   docker build -t ai-qa-radar . && docker run -p 8000:8000 ai-qa-radar
# Works on Hugging Face Spaces (Docker), Koyeb, Railway, a home server, etc. Set PORT if the host requires it.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY digest ./digest
COPY server ./server
COPY web ./web
RUN useradd --create-home radar && chown -R radar /app
USER radar
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/api/health',timeout=4)"
CMD ["python", "-m", "server"]
