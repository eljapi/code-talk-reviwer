# Vertex AI Live API Integration Tests

This directory contains test scripts for validating the Google Vertex AI Live API integration.

## Test Scripts

### 1. `test_vertex_api_integration.py`
Comprehensive integration test that validates:
- Google Cloud authentication
- Vertex AI Live API client connection
- Audio streaming functionality
- Session management
- Full end-to-end integration with audio file streaming

**Usage:**
```bash
python tests/test_vertex_api_integration.py
```

### 2. `test_vertex_auth_curl.py`
Curl-equivalent test that validates:
- REST API authentication
- Streaming endpoint accessibility
- WebSocket endpoint information

**Usage:**
```bash
python tests/test_vertex_auth_curl.py
```

## Prerequisites

### Environment Variables
Set the following environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

Alternatively, you can use Application Default Credentials (ADC) by running:
```bash
gcloud auth application-default login
```

### Dependencies
Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Expected Output

### Successful Test Run
When all tests pass, you should see output like:
```
✅ Authentication successful for project: your-project-id
✅ Connected to Vertex AI Live API, session: uuid-session-id
✅ Created test audio file: test_audio.wav
✅ Successfully streamed 5 audio chunks
✅ Created session: uuid-session-id
✅ Session state is active
...
🎉 All tests passed!
```

### Common Issues

1. **Authentication Failed**
   - Ensure `GOOGLE_CLOUD_PROJECT` is set
   - Verify service account credentials or run `gcloud auth application-default login`
   - Check that the service account has Vertex AI permissions

2. **Connection Timeout**
   - Verify network connectivity
   - Check if Vertex AI API is enabled in your project
   - Ensure the specified region supports Vertex AI Live API

3. **Model Not Found**
   - Verify that the Gemini model is available in your region
   - Check if you have access to the specified model

## Test Coverage

These tests validate the implementation of task 2 requirements:
- ✅ Google Cloud client libraries and authentication setup
- ✅ Bidirectional streaming connection to Vertex AI Live API
- ✅ PCM audio streaming (16 kHz) implementation
- ✅ Session management and connection handling
- ✅ Automatic reconnection capabilities
- ✅ Modular architecture with separate auth, client, streaming, and session components