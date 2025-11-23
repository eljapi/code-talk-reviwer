"""Quick setup and test script for Gemini Live API.

This script helps you:
1. Get the API key
2. Set it in your environment
3. Test the WebSocket connection immediately
"""

import os
import sys
import webbrowser
import subprocess

def main():
    print("🚀 Quick Setup & Test for Gemini Live API")
    print("=" * 50)
    
    # Check if API key is already set
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    
    if api_key:
        print(f"✅ API key found: {api_key[:10]}...")
        print("   Skipping setup, going straight to test!")
        test_connection()
        return
    
    print("\n📋 Step 1: Get Your API Key")
    print("-" * 30)
    print("Opening Google AI Studio in your browser...")
    
    try:
        webbrowser.open("https://aistudio.google.com/app/apikey")
        print("✅ Browser opened!")
    except:
        print("⚠️  Please manually go to: https://aistudio.google.com/app/apikey")
    
    print("\n📝 Instructions:")
    print("1. Sign in with: fotero.solidcore@gmail.com")
    print("2. Click 'Create API Key'")
    print("3. Copy the generated key")
    
    print("\n⏸️  Press Enter after you've copied your API key...")
    input()
    
    print("\n📋 Step 2: Enter Your API Key")
    print("-" * 30)
    api_key = input("Paste your API key here: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return
    
    print(f"✅ API key received: {api_key[:10]}...")
    
    # Set environment variable for current session
    os.environ["GOOGLE_AI_API_KEY"] = api_key
    
    # Update .env file
    print("\n📋 Step 3: Saving to .env file")
    print("-" * 30)
    
    try:
        # Read current .env
        with open(".env", "r") as f:
            lines = f.readlines()
        
        # Update or add API key
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("# GOOGLE_AI_API_KEY=") or line.startswith("GOOGLE_AI_API_KEY="):
                lines[i] = f"GOOGLE_AI_API_KEY={api_key}\n"
                updated = True
                break
        
        if not updated:
            # Add after the comment
            for i, line in enumerate(lines):
                if "Get your API key from:" in line:
                    lines.insert(i + 1, f"GOOGLE_AI_API_KEY={api_key}\n")
                    break
        
        # Write back
        with open(".env", "w") as f:
            f.writelines(lines)
        
        print("✅ API key saved to .env file")
        
    except Exception as e:
        print(f"⚠️  Could not update .env file: {e}")
        print("   You can manually add it later")
    
    # Set for PowerShell session
    print("\n📋 Step 4: Setting for Current Session")
    print("-" * 30)
    print("Run this command in your PowerShell:")
    print(f"$env:GOOGLE_AI_API_KEY='{api_key}'")
    
    print("\n⏸️  Press Enter after running the command above...")
    input()
    
    # Test connection
    test_connection()


def test_connection():
    """Test the WebSocket connection."""
    print("\n🧪 Testing WebSocket Connection")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        print("❌ API key not found in environment")
        print("   Please set it with:")
        print("   $env:GOOGLE_AI_API_KEY='your-api-key'")
        return
    
    print(f"✅ Using API key: {api_key[:10]}...")
    print("\n🔄 Running test script...")
    
    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, "test_with_api_key.py"],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print("\n🎉 Test completed! Check the output above.")
        else:
            print("\n⚠️  Test had some issues. Check the output above.")
            
    except Exception as e:
        print(f"❌ Error running test: {e}")
        print("\n💡 You can manually run:")
        print("   python test_with_api_key.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled. You can run this script again anytime!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Manual setup:")
        print("1. Get API key: https://aistudio.google.com/app/apikey")
        print("2. Set it: $env:GOOGLE_AI_API_KEY='your-key'")
        print("3. Test: python test_with_api_key.py")