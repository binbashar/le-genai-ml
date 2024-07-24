# Generative AI AWS Conference

Este proyecto de Streamlit demuestra varios casos de uso de AI generativa utilizando modelos alojados en AWS.

## Casos de Uso Incluidos

1. Code Generation
2. Basic Translation and NLP Tasks
3. Extract text from images

## Requisitos

- Docker

## Instalación y Ejecución

1. Clona el repositorio:

```bash
git clone <repository-url>
cd <repository-directory>
```

## Run Docker

- docker build -t generative-ai-aws-conference .
- docker run -e USER='YOUR-USER' -e PWD='YOUR-PWD' -e AWS_ACCESS_KEY_ID='YOUR-KEY' -e AWS_SECRET_ACCESS_KEY='SECRET_ACCESS_KEY' -e AWS_SESSION_TOKEN='YOUR-SESSION-TOKEN' -p 8080:8080 generative-ai-aws-conference