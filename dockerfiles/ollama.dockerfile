FROM ollama/ollama:0.6.3

# Install curl
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*


# Create directories for models
RUN mkdir -p /root/.ollama/models

# Pull Ollama models
RUN nohup bash -c "ollama serve &" && \
  while ! curl -s http://localhost:11434/api/health >/dev/null; do sleep 1; done && \
  # curl http://localhost:11434/api/generate -d '{"model": "phi4-mini"}'
  nohup bash -c "ollama pull phi4-mini"
