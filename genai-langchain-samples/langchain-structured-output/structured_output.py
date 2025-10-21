"""
Backend module for structured output with Amazon Bedrock.

Simple rule:
- ChatBedrockConverse (default): Native structured output works for ALL models
- ChatBedrock: Requires JsonOutputParser (use_bedrock_converse=False)
"""

from langchain_aws import ChatBedrock, ChatBedrockConverse
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import Type

from config import Model, get_bedrock_client_kwargs


# Standard response model
class Response(BaseModel):
    """Structured response model."""

    reason: str = Field(description="Reasoning behind the answer")
    answer: str = Field(description="The answer or recommendation")
    confidence: float = Field(description="Confidence level (0-1)", ge=0, le=1)


def get_llm(
    model: Model,
    output: Type[BaseModel] = Response,
    use_bedrock_converse: bool = True
):
    """
    Get structured LLM for any Bedrock model.

    Args:
        model: Model enum
        output: Pydantic model for structured output (default: Response)
        use_bedrock_converse: Use ChatBedrockConverse (default: True) or ChatBedrock (False)

    Returns:
        Structured LLM or Chain depending on the approach

    Examples:
        # Default: ChatBedrockConverse with native structured output
        llm = get_llm(Model.NOVA_MICRO)
        result = llm.invoke("prompt")  # Returns Response model

        # Custom output model
        llm = get_llm(Model.CLAUDE_HAIKU, output=CustomModel)
        result = llm.invoke("prompt")  # Returns CustomModel instance

        # Legacy: ChatBedrock with JsonOutputParser
        llm = get_llm(Model.NOVA_MICRO, use_bedrock_converse=False)
        result = llm.invoke({"query": "prompt"})  # Returns dict
    """

    if use_bedrock_converse:
        # ChatBedrockConverse supports native structured output for ALL models
        llm = ChatBedrockConverse(
            model=model.value.id,
            **model.value.get_params(),
            **get_bedrock_client_kwargs(),
        )
        return llm.with_structured_output(output)

    else:
        # ChatBedrock requires JsonOutputParser
        llm = ChatBedrock(
            model_id=model.value.id,
            model_kwargs=model.value.get_params(),
            **get_bedrock_client_kwargs(),
        )

        parser = JsonOutputParser(pydantic_object=output)

        prompt = PromptTemplate(
            template="{query}\n\n{format_instructions}",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        return prompt | llm | parser