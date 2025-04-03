FROM ollama/ollama:0.6.3

# Create directories for models
RUN mkdir -p /root/.ollama/models

# Pull Ollama models
RUN nohup bash -c "ollama serve &" && sleep 5 && ollama pull phi4-mini
