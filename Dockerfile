FROM python:3.11

# Configure Poetry
ENV POETRY_VERSION=1.8.5
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

# Install poetry separated from system interpreter
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

# Add `poetry` to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /hse_hw3_ap_url_shortener

# Install dependencies
COPY poetry.lock pyproject.toml README.md ./
RUN poetry install

# Run your app
COPY . /hse_hw3_ap_url_shortener
CMD ["poetry", "run", "uvicorn", "hse_hw3_ap_url_shortener.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
