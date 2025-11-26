# Lambda container for filter_gather_data function
# Base: Python 3.13 official AWS Lambda image
FROM public.ecr.aws/lambda/python:3.13

# Install uv (Rust-based package manager - faster than pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /var/task

# Install dependencies directly (no editable install needed for Lambda)
RUN uv pip install --system --no-cache \
    boto3>=1.35.0 \
    pyarrow>=18.1.0 \
    pandas>=2.2.0

# Copy Lambda function code
COPY lambda_function.py ./

# Set Lambda handler
CMD ["lambda_function.lambda_handler"]
