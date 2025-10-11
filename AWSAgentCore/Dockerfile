FROM python:3.10-slim

# Build arguments for AWS configuration
ARG AWS_DEFAULT_REGION=us-east-1
ARG AWS_ACCOUNT_ID=761018845710
ARG IMAGE_TAG=latest

# Set environment variables for encoding and AWS
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf8
ENV AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
ENV AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Use ENTRYPOINT instead of CMD for more reliable execution
ENTRYPOINT ["python", "-u", "strandsAgent.py"]