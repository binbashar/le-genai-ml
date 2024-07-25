# GenAI binbah Leverage AWS Assistant

This Streamlit project demonstrates various use cases of generative AI using models hosted on AWS.

## AWS Cloud Solutions Architecture

[binbash Leverage™ Ref Architecture data-science/us-east-1/genai-llm-rag-bedrock-poc layer](https://github.com/binbashar/le-tf-infra-aws/tree/master/data-science/us-east-1/genai-llm-rag-bedrock-poc%20) 

<a href="https://github.com/binbashar">
    <img src="https://raw.githubusercontent.com/binbashar/le-genai-ml/master/assets/images/genai-llm-rag-bedrock-poc.png" width="1032" align="left" alt="binbash"/>
</a>
<br clear="left"/>

## Included Use Cases

1. Code Generation
2. Basic Translation and NLP Tasks
3. Extracting Text from Images

## Prerequisites

- Docker

## Installation and Execution

1. Clone the repository:

```bash
git clone <repository-url>
cd <repository-directory>
```

2. Build and run the Docker container:

```bash
docker build -t generative-ai-aws-conference .
docker run -e USER='YOUR-USER' -e PWD='YOUR-PWD' -e AWS_ACCESS_KEY_ID='YOUR-KEY' -e AWS_SECRET_ACCESS_KEY='YOUR-SECRET-ACCESS-KEY' -e AWS_SESSION_TOKEN='YOUR-SESSION-TOKEN' -p 8080:8080 generative-ai-aws-conference
```

Replace the environment variables (`YOUR-USER`, `YOUR-PWD`, `YOUR-KEY`, `YOUR-SECRET-ACCESS-KEY`, `YOUR-SESSION-TOKEN`) with your actual AWS credentials and user information.