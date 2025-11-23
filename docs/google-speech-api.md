Google’s Latest Voice APIs for Real‑Time Speech Input/Output (Python)

Building a real-time voice assistant with Google’s ecosystem is now easier thanks to recent updates. Google offers:

Cloud Speech-to-Text (STT) with new Chirp models for streaming transcription.

Cloud Text-to-Speech (TTS) with Chirp 3 HD voices for lifelike speech synthesis.

Vertex AI “Live API” (Gemini) for end-to-end speech-to-speech conversations (voice in and voice out) with minimal latency.

Below, we explore each in turn – focusing on the most up-to-date Python SDKs, streaming mode usage, and code examples.

Google Cloud Speech‑to‑Text (Chirp Models) – Real-Time Transcription

Google’s Cloud STT now uses the Chirp model family (the latest generation of Google’s speech models) to improve accuracy and language coverage
techcrunch.com
techcrunch.com
. In v2 of the Speech-to-Text API, you can perform real-time streaming transcription using these new models. Key features include:

Streaming recognition: Continuously send audio and receive partial transcripts in real time
cloud.google.com
. This is ideal for live voice input or long audio streams.

Multilingual support: Chirp models support over 125 languages/variants
cloud.google.com
 (e.g. language_codes=["en-US"] for English). Google’s latest universal speech model improves multilingual accuracy
cloud.google.com
.

Improved accuracy: Chirp uses advanced neural networks (trained on massive data) for higher accuracy in varied conditions
cloud.google.com
.

Easy integration with Python: Use the google-cloud-speech library (v2) to stream audio from a file or microphone to the API.

Example – Streaming STT in Python (v2 API with Chirp):

from google.cloud import speech_v2 as speech
from google.cloud.speech_v2 import types as speech_types

client = speech.SpeechClient()
# Configure streaming recognition:
config = speech_types.RecognitionConfig(
    auto_decoding_config=speech_types.AutoDetectDecodingConfig(),  # auto-detects PCM encoding
    language_codes=["en-US"],
    model="chirp_3"  # Use the latest Chirp model for STT
)
streaming_config = speech_types.StreamingRecognitionConfig(config=config)
# The 'recognizer' can be a project resource or '_' for default
config_request = speech_types.StreamingRecognizeRequest(
    recognizer=f"projects/{PROJECT_ID}/locations/global/recognizers/_",
    streaming_config=streaming_config
)

# Simulate streaming audio by splitting a WAV file into chunks
with open("audio.wav", "rb") as f:
    audio = f.read()
chunk_size = len(audio) // 5
audio_chunks = [audio[i:i+chunk_size] for i in range(0, len(audio), chunk_size)]

# Generator for requests: first send config, then audio chunks
def request_generator():
    yield config_request
    for chunk in audio_chunks:
        yield speech_types.StreamingRecognizeRequest(audio=chunk)

# Start streaming recognition
responses = client.streaming_recognize(requests=request_generator())
for response in responses:
    for result in response.results:
        print("Transcript:", result.alternatives[0].transcript)


In this example, we load an audio file, chunk it, and stream it to the API. The streaming_recognize iterator yields interim Transcript results in real time
cloud.google.com
. We specify model="chirp_3" to leverage Google’s newest model. Google Cloud handles voice activity detection and will stream back partial and final transcriptions as the audio is processed
cloud.google.com
cloud.google.com
.

Google Cloud Text‑to‑Speech (Chirp 3 HD Voices) – Natural Speech Synthesis

For converting text to spoken audio, Google Cloud TTS now offers Chirp 3 HD voices, delivering highly natural speech output
techcrunch.com
docs.cloud.google.com
. Chirp 3 voices are the latest high-fidelity voices on Vertex AI, supporting 31+ languages with multiple voice personas
techcrunch.com
. Key highlights:

Lifelike voices: Chirp 3 voices use advanced speech synthesis for human-like intonation and expressiveness
techcrunch.com
. They can handle complex sentences with proper pausing and tone, mimicking natural speech patterns.

HD quality & multilingual: Voices are high-definition and available in many languages/genders. For example, "en-US-Chirp3-HD-Leda" is an English female voice, "ja-JP-Chirp3-HD-Leda" a Japanese voice, etc.
tech-blog.abeja.asia
tech-blog.abeja.asia
.

SSML and controls: These voices support SSML for fine control (pronunciations, pauses) and new features like adjustable speaking rate (e.g. speaking_rate in the request)
docs.cloud.google.com
docs.cloud.google.com
.

Streaming or standard synthesis: You can request the API to return audio in one go, or use streaming TTS (new StreamingSynthesize method) to receive audio chunks as the text is synthesized
developers.google.com
gist.github.com
 – helpful for long responses to start playback sooner.

Example – Basic TTS in Python with a Chirp HD voice:

from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()
text_input = texttospeech.SynthesisInput(text="Hello, world! This is Google's Chirp voice.")
# Select a Chirp 3 HD voice by name and language
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Chirp3-HD-Leda"   # Chirp3 HD voice (English, female)
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16  # WAV audio
)
response = client.synthesize_speech(
    input=text_input, voice=voice, audio_config=audio_config
)
# Write the output to a WAV file (16 kHz PCM)
with open("output.wav", "wb") as f:
    f.write(response.audio_content)


This snippet uses the Cloud TTS client to synthesize speech from text using a Chirp3 HD voice
tech-blog.abeja.asia
tech-blog.abeja.asia
. The resulting audio (output.wav) will sound highly natural, reflecting Google’s latest voice model quality. You can adjust voice.name to any available Chirp voice (see Google’s Supported voices list) and choose output format (e.g. MP3, OGG). For real-time needs, the StreamingSynthesize API can be used similarly by sending a stream of text and receiving audio chunks in response
developers.google.com
 (this is a more advanced use-case, often not needed unless responses are very long).

Google Vertex AI Live API – Real-Time Voice Conversations (Speech‑to‑Speech)

For a truly interactive, speech-first assistant, Google’s new Vertex AI Live API (part of the Gemini model family) is the best-fit solution. It provides a bidirectional streaming connection that handles speech-to-text, language understanding (LLM), and text-to-speech in one loop
cloud.google.com
docs.cloud.google.com
. In other words, you can feed live audio from a user, have the AI model (Gemini) process it (with context and even tool calls), and stream back a voice response – all with minimal latency. Key capabilities of the Live API
cloud.google.com
:

Multimodal, two-way streaming – The API “can see, hear, and speak.” It accepts audio (and even video or text) as input and produces audio (and text) as output in a continuous stream
cloud.google.com
cloud.google.com
. This allows natural back-and-forth dialogue.

Low latency + barge-in – It’s optimized for real-time interaction
cloud.google.com
. Partial responses start streaming out quickly, and built-in Voice Activity Detection (VAD) lets users interrupt the AI by speaking over it
docs.cloud.google.com
docs.cloud.google.com
 (the AI will stop talking when it detects the user). This “barge-in” is crucial for a smooth conversation flow.

LLM-powered understanding – Under the hood is Gemini, Google’s advanced language model. The Live API maintains session memory of the conversation
cloud.google.com
 and can follow context over multiple turns. It also supports function calling/tool use during dialogue
cloud.google.com
 (e.g. your assistant can call your code-inspection tool or do web searches mid-conversation, based on the LLM’s decisions).

High-quality voices – The spoken responses use the Chirp 3 HD voices by default, across many languages
docs.cloud.google.com
. You can select the voice and language via config (e.g., choose a male/female voice or switch output language)
docs.cloud.google.com
.

Server-side WebSockets – The Live API uses a WebSocket streaming connection (with the Python SDK handling this under the hood)
cloud.google.com
. This makes it suitable for server-to-server use, and you’d typically relay audio to/from client devices over your own WebRTC or socket layer.

Example – Two-Way Streaming with Vertex AI Live API (Python):

import asyncio
from google import genai

client = genai.Client(vertexai=True, project=GOOGLE_CLOUD_PROJECT, location="global")
# Configure the session to expect audio in and audio out
config = { "response_modalities": ["AUDIO"] }  # can also request text output by adding "TEXT"

async def main():
    async with client.aio.live.connect(model="gemini-live-2.5-flash", config=config) as session:
        # In practice, get audio frames from microphone or client stream:
        audio_frame = get_next_audio_frame()  # PCM bytes at 16 kHz
        await session.send(input={"data": audio_frame, "mime_type": "audio/pcm"})
        # Receive and process streamed responses from the model:
        async for message in session.receive():
            # If the model produced a transcription of user speech:
            if message.server_content.input_transcription:
                user_text = message.server_content.input_transcription.transcript
                print(f"User said: {user_text}")
            # If the model has output (speech) ready:
            if message.server_content.model_turn:
                for part in message.server_content.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        audio_chunk = part.inline_data.data  # chunk of PCM audio
                        play_audio(audio_chunk)  # play or send this chunk to user in real-time


In this pseudo-code, we create a GenAI client and open a live session with the Gemini model. We send audio frames (16 kHz PCM bytes) from the user to the session, and simultaneously listen for responses. The model will transcribe input speech (emitting input_transcription events with text) and generate a voice answer (model_turn parts containing audio data) streamingly. In practice, you would loop continuously: reading microphone input and sending it, while concurrently playing the output audio chunks as they arrive
docs.cloud.google.com
docs.cloud.google.com
. This simultaneous send/receive enables a near real-time conversation – the assistant can start formulating a spoken answer even as the user is finishing their question.

Notably, the Live API handles voice activity detection automatically: as soon as the user starts talking, the model stops its speech and listens, and you can also configure or disable this VAD if needed
docs.cloud.google.com
docs.cloud.google.com
. You can also adjust the voice used for responses by specifying a voice_name in the config (for example, an enthusiastic or calm tone, different languages, etc.)
docs.cloud.google.com
. All of this runs server-side via Python, with the heavy AI processing happening in Google’s cloud. The result is a fluid, interruptible voice conversation powered by Google’s latest LLM and speech models.

Why Vertex Live API is the best fit: It essentially marries STT, an advanced LLM (for reasoning and tool use), and TTS into one streaming pipeline. This minimizes latency (no need to call separate APIs for STT then LLM then TTS) and complexity. As Google describes, it gives end users “the experience of natural, human-like voice conversations” with fast response and the ability to cut in with your voice
cloud.google.com
docs.cloud.google.com
. Given the project goal of a voice-first assistant that can be interrupted and can use tools, Gemini Live is a cutting-edge choice.

Summary and Next Steps

To recap, Google’s updated voice APIs offer a powerful toolkit for real-time voice applications: Cloud STT v2 (Chirp) for accurate streaming transcription, Cloud TTS (Chirp3 HD) for high-quality speech output, and the integrated Vertex AI Live API for full speech-to-speech conversational AI. Each comes with Python SDK support for server-side integration. For your project, the Vertex Live API (Gemini) is likely the one-stop solution – it’s designed for exactly this purpose, handling the entire loop from listening to answering with minimal latency
cloud.google.com
cloud.google.com
.

Before coding, ensure you have enabled the necessary Google Cloud services (Speech-to-Text, Text-to-Speech, Vertex AI) and have credentials set up. Then you can use the examples above as a starting point. With streaming audio handling and perhaps some tool function definitions for the LLM to call, you’ll be on your way to building a near real-time, voice-interruptible assistant leveraging Google’s state-of-the-art speech and language AI. Good luck!

Sources: Recent Google Cloud documentation and announcements were used to ensure up-to-date information (Chirp 3 models, Vertex AI Live API, etc.)
techcrunch.com
docs.cloud.google.com
, along with official code examples for the Python SDKs
cloud.google.com
tech-blog.abeja.asia
. Be sure to consult Google’s docs for any API changes or quota considerations (the Live API is in Preview as of 2025
cloud.google.com
). With the latest tools, your voice assistant will be at the cutting edge of what Google’s AI can do in real time.