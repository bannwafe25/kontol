FROM python:3.13-slim

WORKDIR /app

# System dependencies required by NTgCalls / PyTgCalls
RUN apt-get update && apt-get install -y \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxfixes3 \
    libxdamage1 \
    libxrandr2 \
    libxtst6 \
    libglib2.0-0 \
    libsm6 \
    libice6 \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "src.py"]
