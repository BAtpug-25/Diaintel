FROM --platform=linux/amd64 python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TOKENIZERS_PARALLELISM=false

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.7.1/en_core_web_lg-3.7.1-py3-none-any.whl

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Download DistilBERT for the live analyzer during image build
RUN python -c "from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer; AutoTokenizer.from_pretrained('distilbert-base-uncased').save_pretrained('/models/distilbert-base-uncased'); AutoModel.from_pretrained('distilbert-base-uncased').save_pretrained('/models/distilbert-base-uncased'); AutoTokenizer.from_pretrained('cardiffnlp/twitter-roberta-base-sentiment').save_pretrained('/models/cardiffnlp--twitter-roberta-base-sentiment'); AutoModelForSequenceClassification.from_pretrained('cardiffnlp/twitter-roberta-base-sentiment').save_pretrained('/models/cardiffnlp--twitter-roberta-base-sentiment'); AutoTokenizer.from_pretrained('facebook/bart-large-mnli').save_pretrained('/models/facebook--bart-large-mnli'); AutoModelForSequenceClassification.from_pretrained('facebook/bart-large-mnli').save_pretrained('/models/facebook--bart-large-mnli')"

# Default command (overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


