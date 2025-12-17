"""
Simple chatbot using Pipecat with LiveKit WebRTC transport.

This bot connects to LiveKit as a participant, processes audio streams in real-time,
and responds using STT, LLM, and TTS pipeline.
"""

import os
import asyncio
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.runner import PipelineRunner
from pipecat.frames.frames import LLMRunFrame

# Services
from pipecat.services.openai import OpenAILLMService
from pipecat.services.openai import OpenAITTSService
from pipecat.services.deepgram.stt import DeepgramSTTService

# Processors
from pipecat.processors.aggregators.llm_response import LLMResponseAggregator
from pipecat.processors.aggregators.llm_response import LLMUserResponseAggregator
from pipecat.processors.aggregators.llm_context import LLMContext, LLMContextAggregatorPair

# Transport
from pipecat.transports.livekit.transport import LiveKitTransport, LiveKitParams

# VAD
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

# Load environment variables
load_dotenv()


async def main():
    """Main entry point for the chatbot."""
    
    # Validate required environment variables
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    
    if not all([livekit_url, livekit_api_key, livekit_api_secret, openai_api_key]):
        raise ValueError(
            "Missing required environment variables: "
            "LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, OPENAI_API_KEY"
        )
    
    # Deepgram is optional - if not provided, we'll note it in the error
    if not deepgram_api_key:
        print("Warning: DEEPGRAM_API_KEY not set. STT will not work without it.")
        print("Get your API key from: https://console.deepgram.com/")
    
    # Get room name from environment or use default
    room_name = os.getenv("LIVEKIT_ROOM", "default-room")
    participant_name = os.getenv("LIVEKIT_PARTICIPANT_NAME", "assistant")
    
    print(f"Connecting to LiveKit room: {room_name}")
    print(f"LiveKit URL: {livekit_url}")
    
    # Initialize services
    # STT: Speech-to-Text (using Deepgram)
    if not deepgram_api_key:
        raise ValueError("DEEPGRAM_API_KEY is required for STT functionality")
    
    stt = DeepgramSTTService(api_key=deepgram_api_key)
    
    # LLM: Language Model
    llm = OpenAILLMService(
        api_key=openai_api_key,
        model="gpt-4o-mini",  # Using mini for faster responses
    )
    
    # TTS: Text-to-Speech
    tts = OpenAITTSService(
        api_key=openai_api_key,
        voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
        model="tts-1"
    )
    
    # Setup conversation context
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful and friendly assistant. "
                "Keep your responses concise and natural for voice conversation. "
                "Respond in a conversational, friendly tone."
            )
        }
    ]
    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)
    
    # Setup response aggregators
    user_response_aggregator = LLMUserResponseAggregator()
    llm_response_aggregator = LLMResponseAggregator()
    
    # Configure LiveKit transport
    # Generate token for joining the room
    try:
        from livekit import api
        
        token = api.AccessToken(livekit_api_key, livekit_api_secret) \
            .with_identity(participant_name) \
            .with_name("AI Assistant") \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )) \
            .to_jwt()
    except ImportError:
        # Fallback: use token from environment if livekit package not available
        token = os.getenv("LIVEKIT_TOKEN")
        if not token:
            raise ValueError(
                "LIVEKIT_TOKEN required if livekit package not installed. "
                "Install with: pip install livekit"
            )
    
    transport = LiveKitTransport(
        room_url=livekit_url,
        token=token,
        params=LiveKitParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_in_enabled=False,
            video_out_enabled=False,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    start_secs=0.3,  # Start detecting speech after 300ms
                    stop_secs=0.5,  # Stop after 500ms of silence
                )
            )
        )
    )
    
    # Build the pipeline
    pipeline = Pipeline([
        # Input: Audio from LiveKit
        transport.input(),
        
        # Speech-to-Text
        stt,
        
        # User response aggregation
        user_response_aggregator,
        
        # Context management
        context_aggregator.user(),
        
        # Language Model
        llm,
        
        # LLM response aggregation
        llm_response_aggregator,
        
        # Context management for assistant
        context_aggregator.assistant(),
        
        # Text-to-Speech
        tts,
        
        # Output: Audio to LiveKit
        transport.output(),
    ])
    
    # Create pipeline task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,  # Allow user to interrupt bot
            enable_metrics=True,
        )
    )
    
    # Event handlers
    @transport.event_handler("on_participant_connected")
    async def on_participant_connected(transport, participant):
        """Called when a participant joins the room."""
        print(f"Participant connected: {participant.identity}")
        # Start the conversation
        await task.queue_frames([LLMRunFrame()])
    
    @transport.event_handler("on_participant_disconnected")
    async def on_participant_disconnected(transport, participant):
        """Called when a participant leaves the room."""
        print(f"Participant disconnected: {participant.identity}")
    
    @transport.event_handler("on_room_connected")
    async def on_room_connected(transport, room):
        """Called when bot successfully connects to the room."""
        print(f"Bot connected to room: {room.name}")
    
    @transport.event_handler("on_room_disconnected")
    async def on_room_disconnected(transport, room):
        """Called when bot disconnects from the room."""
        print(f"Bot disconnected from room: {room.name}")
    
    # Run the pipeline
    runner = PipelineRunner()
    try:
        await runner.run(task)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await transport.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
