"""
Nova Sonic 2 POC - Minimal LiveKit Agent

This agent connects to a LiveKit room and bridges audio to/from Nova Sonic 2.
Configured for Brazilian Portuguese (pt-BR) with the Leo voice.
"""

import os
from livekit import agents
from livekit.agents import AgentSession, Agent, AutoSubscribe
from livekit.plugins.aws.experimental.realtime import RealtimeModel

# Voice configuration (pt-BR)
# Run `just patch-voices` to enable native pt-BR voices: leo, carolina
# Options: leo, carolina (pt-BR), tiffany, matthew (polyglot), amy, lupe, carlos, etc.
VOICE_ID = os.environ.get("VOICE_ID", "leo")

# System prompt in Brazilian Portuguese
SYSTEM_PROMPT = """Você é um assistente de IA caloroso, profissional e prestativo.
Responda sempre em português brasileiro.
Dê respostas precisas que soem naturais, diretas e humanas.
Seja breve e conciso, mantendo-se dentro de 3-5 frases curtas."""


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the LiveKit agent."""
    # Connect to the LiveKit room (audio only, no video)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Create the agent with instructions
    agent = Agent(instructions=SYSTEM_PROMPT)

    # Initialize session with Nova Sonic 2 using the configured voice
    session = AgentSession(llm=RealtimeModel(voice=VOICE_ID))

    # Start the bidirectional audio session
    await session.start(room=ctx.room, agent=agent)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
