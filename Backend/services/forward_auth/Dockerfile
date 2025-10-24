FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY forward_auth.py ./
CMD ["python","forward_auth.py"]
