import streamlit as st
import boto3
import json
from langchain_aws import BedrockLLM

# Configurar cliente de Bedrock
aws_region = 'us-east-1'
bedrock_client = boto3.client('bedrock-runtime', region_name=aws_region)

def load_llm():
    """Load the Bedrock LLM."""
    return BedrockLLM(model_id="mistral.mixtral-8x7b-instruct-v0:1", client=bedrock_client)

llm = load_llm()

def run():
    st.header('Translation and NLP')
    text_to_translate = st.text_area('Enter text to translate:')
    target_language = st.selectbox('Select target language:', ['English', 'French', 'German', 'Spanish', 'Italian'])
    
    if st.button('Translate'):
        # Prompt con ejemplos específicos para guiar al modelo
        example_prompts = {
            "English": "Translate the following text to English. Only provide the translated text. Do not include any additional text or explanation.\n\n",
            "French": "Translate the following text to French. Only provide the translated text. Do not include any additional text or explanation.\n\n",
            "German": "Translate the following text to German. Only provide the translated text. Do not include any additional text or explanation.\n\n",
            "Spanish": "Translate the following text to Spanish. Only provide the translated text. Do not include any additional text or explanation.\n\n",
            "Italian": "Translate the following text to Italian. Only provide the translated text. Do not include any additional text or explanation.\n\n",
        }

        prompt = (
            f"{example_prompts[target_language]}"
            f"Input: {text_to_translate}\nOutput:"
        )

        try:
            response = llm.generate(prompts=[prompt], temperature=0.1)

            if response and response.generations and response.generations[0] and response.generations[0][0]:
                translation = response.generations[0][0].text.strip()
                st.text_area('Translated Text:', value=translation, height=200)
            else:
                st.error("No translation was provided.")
        except boto3.exceptions.Boto3Error as e:
            st.error(f"An error occurred: {e}")