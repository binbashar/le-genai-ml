FROM public.ecr.aws/lambda/python:3.13

# Install dependencies
RUN pip install --no-cache-dir pyarrow>=18.1.0 boto3>=1.34.0

# Copy function code to Lambda task root
COPY lambda_function.py /var/task/
COPY schema.py /var/task/
COPY pii_scrubber.py /var/task/
COPY parquet_storage.py /var/task/

# Set the working directory
WORKDIR /var/task

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]
