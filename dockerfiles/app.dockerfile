# Download transformers models
FROM python:3.12-slim as transformers-downloader

# Create directories for models
RUN mkdir -p /root/.cache/huggingface

# Install Python dependencies for transformers
RUN pip install --no-cache-dir transformers torch torchvision einops

# Pull transformer models
RUN python -c "from transformers import AutoModel, AutoImageProcessor; model = AutoModel.from_pretrained('nomic-ai/nomic-embed-vision-v1.5', trust_remote_code=True); processor = AutoImageProcessor.from_pretrained('nomic-ai/nomic-embed-vision-v1.5')"

# Stage 3: Final runtime image
FROM python:3.12-slim as runtime

# Install system dependencies
# RUN apt-get update && apt-get install -y \
#   curl \
#   && rm -rf /var/lib/apt/lists/*

# Install Ollama
# RUN curl -fsSL https://ollama.com/install.sh | sh

# Create necessary directories
RUN mkdir -p /root/.cache/huggingface

# Copy models from downloader stage
COPY --from=transformers-downloader /root/.cache/huggingface /root/.cache/huggingface

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY poetry.lock pyproject.toml ./

RUN pip install --no-cache-dir poetry && \
  poetry config virtualenvs.create false && \
  poetry install --no-interaction --no-ansi --no-root

# Copy the application code
COPY tagger ./tagger

# Start FastAPI server
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]