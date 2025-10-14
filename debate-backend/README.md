# Debate Backend

FastAPI backend for the autogen debate team application with WebSocket support for real-time agent conversation streaming and user interaction.

## Architecture

- **FastAPI**: Web framework with WebSocket support
- **Autogen**: Multi-agent conversation framework
- **Pydantic**: Data validation and serialization
- **JSON Persistence**: Conversation tree state management

## Project Structure

```
debate-backend/
├── main.py                 # FastAPI application with CORS
├── models.py               # Pydantic models for WebSocket messages
├── state_manager.py        # Conversation tree state management
├── debate_team.py          # Debate team setup (5 agents)
├── requirements.txt        # Python dependencies
├── pytest.ini              # Pytest configuration
├── .env.example            # Environment variable template
├── README.md               # This file
└── tests/                  # Test suite
    ├── __init__.py
    ├── test_models.py
    └── test_state_manager.py
```

## Setup

### Prerequisites

- Python 3.13+
- OpenAI API key

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `STATE_FILE_PATH`: Path to JSON file for conversation state (default: `conversation_state.json`)
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins (default: `http://localhost:8001`)

## Running the Application

Development mode with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_models.py -v
```

## Debate Team Configuration

The debate team consists of 5 agents:
1. **Jara_Supporter**: Passionate left-wing supporter
2. **Kast_Supporter**: Right-wing/conservative supporter
3. **Neural_Agent**: AI observer asking clarifying questions
4. **Moderate_Left**: Center-left pragmatic supporter
5. **Moderate_Right**: Center-right business-friendly supporter

All agents use GPT-4o-mini model with specific system messages to maintain their political perspectives.

## WebSocket API

WebSocket endpoint: `ws://localhost:8000/ws/debate` (to be implemented in Task 1.3)

### Message Types

- `agent_message`: Message from an agent
- `user_interrupt`: Request to pause conversation
- `user_directed_message`: User message to specific agent with optional branching
- `interrupt_acknowledged`: Confirmation of interrupt
- `stream_end`: Conversation ended
- `error`: Error notification
- `tree_update`: Full tree state update

## Development

### Code Quality

- All code is fully typed (no `any` types)
- Pydantic models validate all inputs
- Comprehensive test coverage
- Async/await patterns for all I/O operations

### Error Handling

- Throw errors early rather than using fallbacks
- Proper validation at all boundaries
- Detailed error messages for debugging

## Next Steps

- Task 1.3: Implement WebSocket endpoint for real-time communication
- Task 1.5: Enhance tree builder for D3.js visualization
