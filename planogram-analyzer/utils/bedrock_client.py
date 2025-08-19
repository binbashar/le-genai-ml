import boto3
import json
import base64
import os
from typing import Dict, Any

class BedrockClient:
    def __init__(self, model_id: str, region: str = "us-east-1"):
        self.model_id = model_id
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
    
    def analyze_compliance(self, planogram_b64: str, realogram_b64: str, 
                         prompt: str, json_structure: Dict, 
                         temperature: float = 0.1, max_tokens: int = 4096) -> Dict:
        """Analyze planogram compliance using selected model"""
        
        # Build the complete prompt
        full_prompt = prompt
        if json_structure:
            full_prompt += f"\n\nJSON de estructura del planograma:\n```json\n{json.dumps(json_structure, indent=2, ensure_ascii=False)}\n```"
        
        # Prepare request based on model type
        if "anthropic" in self.model_id:
            request_body = self._prepare_anthropic_request(
                planogram_b64, realogram_b64, full_prompt, temperature, max_tokens
            )
        elif "meta" in self.model_id:
            request_body = self._prepare_llama_request(
                planogram_b64, realogram_b64, full_prompt, temperature, max_tokens
            )
        else:
            raise ValueError(f"Unsupported model: {self.model_id}")
        
        # Invoke model
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract result based on model type
        if "anthropic" in self.model_id:
            result_text = response_body.get('content', [{}])[0].get('text', '{}')
        elif "meta" in self.model_id:
            result_text = response_body.get('generation', '{}')
        else:
            result_text = '{}'
        
        # Try to parse as JSON
        try:
            # Clean the response text
            result_text = result_text.strip()
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            return json.loads(result_text)
        except:
            return {"raw_response": result_text, "error": "Could not parse JSON response"}
    
    def _prepare_anthropic_request(self, planogram_b64: str, realogram_b64: str, 
                                  prompt: str, temperature: float, max_tokens: int) -> Dict:
        """Prepare request for Anthropic models"""
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": planogram_b64
                            }
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": realogram_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
    
    def _prepare_llama_request(self, planogram_b64: str, realogram_b64: str, 
                              prompt: str, temperature: float, max_tokens: int) -> Dict:
        """Prepare request for Llama models"""
        return {
            "prompt": f"[Image 1: Planogram]\n[Image 2: Realogram]\n\n{prompt}",
            "images": [planogram_b64, realogram_b64],
            "max_gen_len": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }