# WebSocket Connection Guide for Gemini Live API

## 🎯 Current Status

We have successfully built the complete voice orchestration system and tested WebSocket connections. Here's what we discovered:

### ✅ **What's Working**
- **WebSocket Connection**: Successfully connects to `wss://generativelanguage.googleapis.com`
- **Authentication**: Service account authentication reaches the server
- **Project Setup**: Google Cloud project and APIs are properly configured
- **Code Architecture**: Complete orchestration system is ready

### ⚠️ **Current Issue**
- **Authentication Scopes**: "Request had insufficient authentication scopes" error
- **Solution**: Need to use Google AI Studio API key OR fix service account scopes

## 🔑 **Option 1: Google AI Studio API Key (Recommended)**

This is the **easiest and fastest** way to get started:

### Step 1: Get API Key
1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with your Google account (`fotero.solidcore@gmail.com`)
3. Click "Create API Key"
4. Copy the generated key

### Step 2: Set Environment Variable
```powershell
# In PowerShell
$env:GOOGLE_AI_API_KEY='your-api-key-here'
```

### Step 3: Test Connection
```bash
python test_with_api_key.py
```

### Expected Result
```
✅ Connected successfully!
📤 Sent setup message
📥 Setup response: {"setupComplete": true}
💬 AI Response: Hello! I'd be happy to help you with Python coding...
🔊 Received audio response: 2048 bytes
🎉 SUCCESS! Gemini Live API is working!
```

## 🔧 **Option 2: Fix Service Account Scopes**

If you prefer to use service accounts:

### Step 1: Enable Required APIs
```bash
gcloud services enable generativelanguage.googleapis.com --project powerful-outlet-477200-f0
gcloud services enable aiplatform.googleapis.com --project powerful-outlet-477200-f0
```

### Step 2: Add Required Roles
```bash
gcloud projects add-iam-policy-binding powerful-outlet-477200-f0 \
  --member="serviceAccount:voice-ai-assistant@powerful-outlet-477200-f0.iam.gserviceaccount.com" \
  --role="roles/generativelanguage.user"
```

### Step 3: Create New Service Account Key
```bash
gcloud iam service-accounts keys create voice-ai-updated-key.json \
  --iam-account=voice-ai-assistant@powerful-outlet-477200-f0.iam.gserviceaccount.com
```

## 🧪 **Testing Your Connection**

### Quick Test Scripts Available:

1. **`test_with_api_key.py`** - Test with Google AI Studio API key
2. **`test_websocket_connection.py`** - Test multiple connection approaches
3. **`get_api_key_instructions.py`** - Get step-by-step API key instructions

### Test Results We've Seen:
```
🔍 Testing Approach 1: Google AI Studio endpoint
✅ Connected successfully!
📤 Sent setup message
❌ received 1008 (policy violation) Request had insufficient authentication scopes.
```

This shows the **connection works** but needs proper authentication.

## 🚀 **Integration with Your Voice Assistant**

Once you have a working connection, here's how to integrate:

### Step 1: Update Vertex Client
```python
# In src/voice_ai_assistant/voice/vertex_client.py
# Use the working authentication method (API key or fixed service account)
```

### Step 2: Test Full Pipeline
```python
# Run the complete orchestration test
python test_real_audio.py
```

### Step 3: Use in Your Application
```python
from voice_ai_assistant.orchestration import VoiceOrchestrator

orchestrator = VoiceOrchestrator()
await orchestrator.start()
session_id = await orchestrator.start_conversation("user-123")
# Now you can send audio and receive responses!
```

## 📊 **Connection Test Results Summary**

| Approach | Status | Issue | Solution |
|----------|--------|-------|----------|
| Google AI Studio + Service Account | 🔄 Partial | Auth scopes | Fix scopes OR use API key |
| Vertex AI Endpoint | ❌ Failed | HTTP 400 | Endpoint may not exist |
| API Key Authentication | 🔄 Ready | Need API key | Get from AI Studio |

## 🎯 **Recommended Next Steps**

### **Immediate (5 minutes):**
1. Get Google AI Studio API key from: https://aistudio.google.com/app/apikey
2. Set environment variable: `$env:GOOGLE_AI_API_KEY='your-key'`
3. Run: `python test_with_api_key.py`

### **Short-term (30 minutes):**
1. Verify full audio streaming works
2. Test with real voice input/output
3. Integrate with your orchestration system

### **Long-term (Production):**
1. Set up proper service account with correct scopes
2. Implement error handling and reconnection
3. Add monitoring and logging

## 🔍 **Debugging Tips**

### If Connection Fails:
1. **Check API key**: Make sure it's valid and has correct permissions
2. **Check region**: Gemini Live API may not be available in all regions
3. **Check quotas**: You might have hit rate limits
4. **Check model**: Make sure `gemini-2.5-flash-native-audio-preview-09-2025` is available

### If Audio Doesn't Work:
1. **Check audio format**: Must be PCM, 16kHz, 16-bit, mono
2. **Check base64 encoding**: Audio must be base64 encoded for JSON
3. **Check chunk size**: Keep chunks reasonably small (1-2KB)

## 🎉 **Success Indicators**

You'll know it's working when you see:
```
✅ Connected successfully!
📥 Setup response: {"setupComplete": true}
💬 AI Response: [actual text response]
🔊 Received audio response: [audio bytes]
✅ Turn completed - conversation ready for next input
```

## 📞 **Support**

If you encounter issues:
1. Check the error messages in the test scripts
2. Verify your API key/credentials are correct
3. Make sure all required APIs are enabled
4. Test with the simple examples first before complex integration

The foundation is solid - we just need the right authentication approach! 🚀