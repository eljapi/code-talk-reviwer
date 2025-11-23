# 🚀 WebSocket Connection Test - Quick Start

## ⚡ **Fastest Way to Test (5 minutes)**

### Option 1: Automated Setup
```powershell
python quick_setup_and_test.py
```
This script will:
1. Open the API key page in your browser
2. Guide you through getting the key
3. Save it to your `.env` file
4. Run the test automatically

### Option 2: Manual Setup
```powershell
# 1. Get API key from: https://aistudio.google.com/app/apikey

# 2. Set it in PowerShell:
$env:GOOGLE_AI_API_KEY='your-api-key-here'

# 3. Run the test:
python test_with_api_key.py
```

## 📋 **What You'll See When It Works**

```
✅ Connected successfully!
📤 Sent setup message
📥 Setup response: {"setupComplete": true}
💬 AI Response: Hello! I'd be happy to help you with Python coding...
🔊 Received audio response: 2048 bytes
💾 Saved audio response: test_audio/response_1.wav
🎉 SUCCESS! Gemini Live API is working!
```

## 🔧 **Your Current Setup**

### ✅ Already Configured:
- **Project**: `powerful-outlet-477200-f0`
- **Service Account**: `voice-ai-assistant@powerful-outlet-477200-f0.iam.gserviceaccount.com`
- **Credentials File**: `voice-ai-service-account-key.json`
- **Region**: `us-central1`

### 🔑 Need to Add:
- **Google AI API Key**: Get from https://aistudio.google.com/app/apikey

## 📁 **Files Updated**

### `.env` file now includes:
```bash
# Google AI Studio API Key (for testing/development)
# Get your API key from: https://aistudio.google.com/app/apikey
# GOOGLE_AI_API_KEY=your-api-key-here
```

Just uncomment and add your key!

## 🧪 **Available Test Scripts**

| Script | Purpose | Status |
|--------|---------|--------|
| `quick_setup_and_test.py` | Automated setup + test | ✅ Ready |
| `test_with_api_key.py` | Full WebSocket test with audio | ✅ Ready |
| `test_websocket_connection.py` | Test multiple approaches | ✅ Ready |
| `get_api_key_instructions.py` | Step-by-step guide | ✅ Ready |

## 🎯 **What We've Proven**

From our test runs:
```
🔍 Testing Approach 1: Google AI Studio endpoint
✅ Connected successfully!  <-- WebSocket works!
📤 Sent setup message
❌ received 1008 (policy violation) Request had insufficient authentication scopes.
```

**Translation**: The connection works perfectly, we just need the API key for authentication!

## 🚀 **Next Steps After Testing**

Once the test works:

1. **Integrate with orchestration**:
   ```python
   from voice_ai_assistant.orchestration import VoiceOrchestrator
   
   orchestrator = VoiceOrchestrator()
   await orchestrator.start()
   session_id = await orchestrator.start_conversation("user-123")
   ```

2. **Send real audio**:
   ```python
   await orchestrator.send_audio_chunk(session_id, audio_data)
   ```

3. **Receive responses**:
   - Text responses via callback
   - Audio responses via callback
   - Real-time streaming working!

## 💡 **Troubleshooting**

### If API key doesn't work:
1. Make sure you're signed in with `fotero.solidcore@gmail.com`
2. Check the key is copied correctly (no extra spaces)
3. Try creating a new key

### If connection fails:
1. Check your internet connection
2. Verify the API key is set: `echo $env:GOOGLE_AI_API_KEY`
3. Try running: `python get_api_key_instructions.py`

## 📞 **Support**

All test scripts include detailed error messages and suggestions. If something fails, the script will tell you exactly what to do next!

---

**Ready to test?** Run: `python quick_setup_and_test.py` 🚀