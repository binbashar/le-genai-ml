FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

RUN useradd --create-home bedrock_agentcore

COPY pyproject.toml uv.lock* ./
RUN uv pip install --system .

COPY . .

USER bedrock_agentcore

EXPOSE 8080

ENTRYPOINT ["opentelemetry-instrument", "python", "-m", "voice_agent"]
