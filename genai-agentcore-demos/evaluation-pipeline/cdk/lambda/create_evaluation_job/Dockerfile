# Create Evaluation Job Lambda
# Minimal container - only needs boto3 (included in Lambda runtime)
#
# Uses Amazon Linux 2023-based Lambda image for Python 3.13
# Architecture: x86_64 (matches CDK bundling)

FROM public.ecr.aws/lambda/python:3.13

# Copy requirements and install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy function code
COPY lambda_function.py ./

# Set Lambda handler
CMD ["lambda_function.lambda_handler"]
