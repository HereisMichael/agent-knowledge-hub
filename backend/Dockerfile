FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/data /app/privacy-ledger \
    && chown -R app:app /app
ENV PYTHONPATH=/app
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
