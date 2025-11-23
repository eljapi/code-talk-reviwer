
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from voice_ai_assistant.voice.vertex_client import VertexLiveClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    
    client = VertexLiveClient(
        model=os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash-native-audio-preview-09-2025")
    )
    
    audio_received = False
    
    def on_audio(data):
        nonlocal audio_received
        audio_received = True
        logger.info(f"Received audio chunk: {len(data)} bytes")
        
    client.set_audio_response_callback(on_audio)
    
    await client.connect()
    
    logger.info("Connected. Sending text message...")
    await client.send_text_message("Hello, can you hear me?")
    
    # Wait for response
    try:
        await asyncio.wait_for(client.listen_for_responses(), timeout=10)
    except asyncio.TimeoutError:
        logger.info("Timeout waiting for response loop (expected if we don't close)")
    except Exception as e:
        logger.error(f"Error: {e}")
        
    await client.disconnect()
    
    if audio_received:
        logger.info("SUCCESS: Audio response received for text message.")
    else:
        logger.info("FAILURE: No audio response received.")

if __name__ == "__main__":
    asyncio.run(main())
