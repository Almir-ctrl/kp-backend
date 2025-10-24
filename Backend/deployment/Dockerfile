# Use NVIDIA CUDA base image for GPU support
FROM nvidia/cuda:13.0.1-cudnn-devel-ubuntu24.04

WORKDIR /app

# Install Python 3 and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set python3.13 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Copy requirements first for better caching
COPY requirements-prod.txt .



# Install PyTorch Nightly (torch, torchvision) for CUDA 13.0 (cu130)
RUN pip install --no-cache-dir --break-system-packages --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu130

# Install other requirements
RUN pip install --no-cache-dir --break-system-packages -r requirements-prod.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p uploads outputs

# Set environment variables
ENV PYTHONPATH=/app
# Point to host Backend/ directory inside container
ENV FLASK_APP=Backend/app.py
ENV PATH="/usr/local/bin:${PATH}"

# Expose port
EXPOSE 8000

# Use python -m to run gunicorn to ensure it's found
CMD ["python", "-m", "gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]