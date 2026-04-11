FROM python:3.12-slim

WORKDIR /app

# Use Tsinghua mirrors
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install poetry (cached layer)
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple poetry

# Configure poetry (cached layer)
RUN poetry config virtualenvs.create false && \
    poetry config repositories.tsinghua https://pypi.tuna.tsinghua.edu.cn/simple/

# Copy dependency files (invalidates cache only when deps change)
COPY pyproject.toml poetry.lock* ./

# Install dependencies (re-runs only when pyproject.toml/poetry.lock changes)
RUN poetry source add --priority=primary tsinghua https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    poetry install --only main --no-interaction --no-ansi --no-root

# Clean up poetry (cached layer after deps are stable)
RUN pip uninstall -y poetry

# Copy application code
COPY conductor/ ./conductor/
COPY demo.sh ./
RUN chmod +x demo.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "conductor.cli", "--help"]
