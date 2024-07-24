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

def process_response(response_text):
    """Process the LLM response to separate code and Docker instructions."""
    # Remove markdown code blocks and strip any leading/trailing whitespace
    cleaned_text = response_text.replace("```", "").strip()
    
    # Split into lines and remove lines that contain only a language name
    lines = cleaned_text.split('\n')
    language_names = ["python", "java", "javascript", "go", "c++", "ruby"]
    code_lines = [line for line in lines if line.lower() not in language_names]
    
    cleaned_text = "\n".join(code_lines)
    
    # Separate code and instructions
    if "Docker instructions:" in cleaned_text:
        code, instructions = cleaned_text.split("Docker instructions:", 1)
    else:
        code = cleaned_text
        instructions = ""
    
    return code.strip(), instructions.strip()

def run():
    st.header('Code Generation')
    prompt = st.text_area('Enter your prompt for code generation:', 'Write a function that reverses a string.')
    language = st.selectbox('Select programming language:', ['Python', 'Java', 'JavaScript', 'C++', 'Ruby', 'Go'])
    if st.button('Generate Code'):
        try:
            prompt = (
                f"Generate a {language} script that accomplishes the following task:\n"
                f"{prompt}\n\n"
                f"The script should be ready to run and include comments explaining the code. "
                f"Also, include Docker instructions to run the script. "
                f"Make sure the script is fully functional and can be copied and executed without errors.\n\n"
                f"Script code:"
            )
            response = llm.generate(prompts=[prompt], temperature=0.1)
            if response.generations:
                generated_code, docker_instructions = process_response(response.generations[0][0].text)
                st.code(generated_code, language=language.lower())
                if docker_instructions:
                    st.markdown("#### Docker Instructions")
                    st.markdown(
                        "1. Create a new directory for the project and navigate to it in your terminal.\n"
                        "2. Create a new file named `Dockerfile` in the project directory and paste the following content:\n"
                        f"```dockerfile\n{docker_instructions.strip()}\n```\n"
                        "3. Create a new file named `requirements.txt` in the project directory and add the following content:\n"
                        "```\n# No dependencies needed for this simple script\n```\n"
                        "4. Build the Docker image by running the following command in the terminal:\n"
                        "```bash\n"
                        "docker build -t reversed-string-app .\n"
                        "```\n"
                        "5. Run the Docker container by executing the following command:\n"
                        "```bash\n"
                        "docker run -p 4000:80 reversed-string-app\n"
                        "```\n"
                        "6. Open your web browser and navigate to `http://localhost:4000`. You should see the reversed string displayed on the page."
                    )
            else:
                st.error("No generation was provided.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

