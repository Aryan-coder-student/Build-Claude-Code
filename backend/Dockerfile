FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir -e .
ENV DEMO_SALES_DATABASE_URL=sqlite:////data/demo_sales.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
