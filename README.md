# Voice-Enabled AI Coding Assistant

A real-time conversational system that allows developers to interact with AI using natural voice commands for intelligent code assistance.

## Features

- **Real-time Voice Interaction**: Natural voice conversations using Google Vertex AI Live API
- **Intelligent Agent Orchestration**: Powered by Strands Agents Framework with Claude Sonnet 4.5
- **Secure Code Operations**: Repository access and operations via Claude Code SDK
- **Multi-language Support**: Works with any programming language repository
- **Built-in Security**: Sandboxed execution and permission controls

## Technology Stack

- **Python 3.10+**: Core runtime environment
- **Strands Agents Framework (v1.14.0+)**: Agent orchestration and conversation management
- **Claude Code SDK (v0.1.6+)**: Secure repository operations and code analysis
- **Google Vertex AI Live API**: Integrated speech-to-speech conversations
- **FastAPI**: Web framework for API endpoints
- **WebSockets**: Real-time audio streaming

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Google Cloud account with Vertex AI API enabled
- Claude API access

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd voice-ai-coding-assistant
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

### Configuration

1. Set up Google Cloud credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Development

Run tests:
```bash
pytest
```

Format code:
```bash
black src tests
isort src tests
```

Type checking:
```bash
mypy src
```

## Project Structure

```
voice-ai-coding-assistant/
├── src/voice_ai_assistant/
│   ├── voice/          # Voice interface layer
│   ├── agent/          # Agent orchestration layer
│   ├── code/           # Code operations layer
│   └── config/         # Configuration management
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── pyproject.toml      # Project configuration
├── requirements.txt    # Production dependencies
└── requirements-dev.txt # Development dependencies
```

## License

MIT License - see LICENSE file for details.