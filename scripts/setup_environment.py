"""Setup script to configure the environment for Voice AI Assistant."""

import os
import sys
from pathlib import Path

def setup_environment():
    """Set up environment variables and configuration."""
    
    print("🚀 Setting up Voice AI Assistant Environment")
    print("=" * 50)
    
    # Check if credentials file exists
    credentials_file = "voice-ai-service-account-key.json"
    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file not found: {credentials_file}")
        print("Please make sure you have downloaded the service account key.")
        return False
    
    # Set environment variables
    env_vars = {
        "GOOGLE_APPLICATION_CREDENTIALS": credentials_file,
        "GOOGLE_CLOUD_PROJECT": "powerful-outlet-477200-f0",
        "VERTEX_AI_REGION": "us-central1",
        "VERTEX_AI_MODEL": "gemini-2.5-flash-native-audio-preview-09-2025",
        "VERTEX_AI_VOICE": "Puck",
        "MAX_CONCURRENT_SESSIONS": "10",
        "SESSION_TIMEOUT_MINUTES": "30",
        "MAX_RESPONSE_LATENCY_MS": "300"
    }
    
    print("Setting environment variables:")
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"  ✅ {key} = {value}")
    
    # Update .env file
    env_content = "\n".join([f"{key}={value}" for key, value in env_vars.items()])
    
    with open(".env", "w") as f:
        f.write("# Voice AI Assistant Configuration\n")
        f.write("# Generated automatically - do not edit manually\n\n")
        f.write(env_content)
    
    print(f"\n✅ Updated .env file with configuration")
    
    # Test the setup
    print("\n🧪 Testing configuration...")
    
    try:
        sys.path.insert(0, "src")
        from voice_ai_assistant.config.settings import settings
        
        print(f"  ✅ Project: {settings.google_cloud_project}")
        print(f"  ✅ Region: {settings.vertex_ai_region}")
        print(f"  ✅ Model: {settings.vertex_ai_model}")
        print(f"  ✅ Voice: {settings.vertex_ai_voice}")
        
    except Exception as e:
        print(f"  ❌ Error loading settings: {e}")
        return False
    
    print("\n🎉 Environment setup complete!")
    print("\nNext steps:")
    print("1. Run: python test_credentials.py")
    print("2. Run: python examples/voice_orchestration_demo.py")
    print("3. Start building your voice AI assistant!")
    
    return True

if __name__ == "__main__":
    success = setup_environment()
    if not success:
        sys.exit(1)