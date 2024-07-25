# Use the official lightweight Python image.
FROM python:3.9-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Set working directory
WORKDIR /app

# Copy local code to the container image.
COPY . /app

# Create the .streamlit directory and the secrets file
RUN mkdir -p /root/.streamlit && \
    echo '[server]' > /root/.streamlit/config.toml && \
    echo 'headless = true' >> /root/.streamlit/config.toml && \
    echo 'port = 8080' >> /root/.streamlit/config.toml && \
    echo 'enableCORS = false' >> /root/.streamlit/config.toml && \
    echo 'enableXsrfProtection = false' >> /root/.streamlit/config.toml
    
# Install dependencies
RUN apt-get update && apt-get install -y tesseract-ocr
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]

# docker build -t generative-ai-aws-assistant .
# docker run \
#-e USER='YOUR-USER' \
#-e PWD='YOUR-PWD' \
#-e AWS_ACCESS_KEY_ID='YOUR-KEY' \
#-e AWS_SECRET_ACCESS_KEY='SECRET_ACCESS_KEY' \
#-e AWS_SESSION_TOKEN='YOUR-SESSION-TOKEN' \
#-p 8080:8080 generative-ai-aws-assistant