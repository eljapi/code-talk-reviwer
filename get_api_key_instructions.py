"""Instructions for getting Google AI Studio API key."""

import os
import webbrowser

def show_api_key_instructions():
    """Show step-by-step instructions for getting API key."""
    
    print("🔑 How to Get Google AI Studio API Key")
    print("=" * 50)
    
    print("\n📋 Step-by-step instructions:")
    print("1. 🌐 Go to Google AI Studio")
    print("2. 🔐 Sign in with your Google account")
    print("3. 🔑 Create a new API key")
    print("4. 📋 Copy the API key")
    print("5. ⚙️  Set it as environment variable")
    
    print("\n🌐 Opening Google AI Studio in your browser...")
    try:
        webbrowser.open("https://aistudio.google.com/app/apikey")
        print("✅ Browser opened successfully")
    except Exception as e:
        print(f"❌ Could not open browser: {e}")
        print("   Please manually go to: https://aistudio.google.com/app/apikey")
    
    print("\n⚙️  After getting your API key, set it with:")
    print("   Windows PowerShell:")
    print("   $env:GOOGLE_AI_API_KEY='your-api-key-here'")
    print("\n   Windows CMD:")
    print("   set GOOGLE_AI_API_KEY=your-api-key-here")
    print("\n   Linux/Mac:")
    print("   export GOOGLE_AI_API_KEY='your-api-key-here'")
    
    print("\n🧪 Then test the connection with:")
    print("   python test_with_api_key.py")
    
    # Check if API key is already set
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if api_key:
        print(f"\n✅ API key is already set: {api_key[:10]}...")
        print("   You can run the test now!")
    else:
        print("\n⚠️  No API key found in environment variables")
        
    print("\n💡 Tips:")
    print("   - Keep your API key secure and don't share it")
    print("   - The API key is free for testing with rate limits")
    print("   - For production, consider using service accounts")


if __name__ == "__main__":
    show_api_key_instructions()