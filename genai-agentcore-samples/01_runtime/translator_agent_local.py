from langgraph.graph import StateGraph, MessagesState
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
import random

# Define the agent using LangGraph
def create_agent():
    """Create and configure the LangGraph agent"""
    # Initialize Bedrock Nova Micro model
    llm = ChatBedrock(
        model_id="us.amazon.nova-micro-v1:0",
        model_kwargs={"temperature": 0.1}
    )

    # System message for translation
    system_message = "You are a translator. Translate the user's message to English. Return ONLY the English translation, nothing else."

    # Define the translator node
    def translator(state: MessagesState):
        # Add system message if not already present
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_message)] + messages

        response = llm.invoke(messages)
        return {"messages": [response]}

    # Create the graph
    graph_builder = StateGraph(MessagesState)

    # Add node
    graph_builder.add_node("translator", translator)

    # Set entry point
    graph_builder.set_entry_point("translator")

    # Compile the graph
    return graph_builder.compile()

# Initialize the agent
agent = create_agent()

def translate(payload):
    """
    Invoke the translator agent with a payload
    """
    user_input = payload.get("prompt")

    # Create the input in the format expected by LangGraph
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    # Extract the final message content
    return response["messages"][-1].content

if __name__ == "__main__":
    # Example phrases in different languages
    example_phrases = [
        "Hola, ¿cómo estás?",
        "Bonjour, comment allez-vous?",
        "Guten Tag, wie geht es Ihnen?",
        "Ciao, come stai?",
        "Olá, como você está?",
        "こんにちは、お元気ですか？",
        "你好，你好吗？",
        "Привет, как дела?"
    ]

    print("\n" + "="*60)
    print("TRANSLATOR AGENT - INTERACTIVE DEMO")
    print("="*60)
    print("\nEnter text to translate to English (Enter for random example):")
    print()

    user_input = input("> ").strip()

    if not user_input:
        user_input = random.choice(example_phrases)
        print(f"[Selected random phrase: {user_input}]\n")

    print("🔄 Translating to English...\n")

    response = translate({"prompt": user_input})

    print(f"✓ Translation: {response}")
    print("\n" + "="*60 + "\n")