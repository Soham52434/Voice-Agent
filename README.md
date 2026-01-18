# Voice Agent - Appointment Booking Assistant

A voice-based appointment booking agent built with **LiveKit Agents**.

## Architecture

```
User speaks → LiveKit WebRTC → Agent Worker
                                    │
                                    ▼
                              ┌─────────────┐
                              │ Silero VAD  │  Voice Activity Detection
                              └─────┬───────┘
                                    │
                                    ▼
                              ┌─────────────┐
                              │Deepgram STT │  Speech-to-Text
                              └─────┬───────┘
                                    │
                                    ▼
                              ┌─────────────┐
                              │ OpenAI LLM  │  Intent + Tool Calling
                              └─────┬───────┘
                                    │
                                    ▼
                              ┌─────────────┐
                              │Cartesia TTS │  Text-to-Speech
                              └─────┬───────┘
                                    │
                                    ▼
                              LiveKit WebRTC → User hears response
```

## Stack

| Component | Provider | Purpose |
|-----------|----------|---------|
| Voice Pipeline | LiveKit Agents | WebRTC, orchestration |
| STT | Deepgram Nova-2 | Speech recognition |
| LLM | OpenAI GPT-4o-mini | Conversation + tools |
| TTS | Cartesia Sonic-2 | Voice synthesis |
| VAD | Silero | Endpoint detection |
| Database | Supabase | Appointments storage |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `backend/.env` and fill in your API keys:

```bash
cp .env.example backend/.env
```

Required keys:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` - from [LiveKit Cloud](https://cloud.livekit.io)
- `DEEPGRAM_API_KEY` - from [Deepgram](https://console.deepgram.com)
- `CARTESIA_API_KEY` - from [Cartesia](https://cartesia.ai)
- `OPENAI_API_KEY` - from [OpenAI](https://platform.openai.com)
- `SUPABASE_URL`, `SUPABASE_KEY` - optional, from [Supabase](https://supabase.com)

### 3. Run the agent

```bash
# Development mode (auto-reloads)
python backend/main.py dev

# Production mode
python backend/main.py start
```

### 4. Connect a frontend

Use LiveKit's [Agents Playground](https://agents-playground.livekit.io) to test, or build your own frontend with the [LiveKit Client SDK](https://docs.livekit.io/client-sdk/).

## Database Schema (Supabase)

If using Supabase, create these tables:

```sql
-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_number TEXT UNIQUE NOT NULL,
  name TEXT DEFAULT 'User',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Appointments
CREATE TABLE appointments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_number TEXT REFERENCES users(contact_number),
  date DATE NOT NULL,
  time TIME NOT NULL,
  status TEXT DEFAULT 'booked',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation logs
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_number TEXT,
  summary TEXT,
  actions JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Project Structure

```
Voice-Agent/
├── backend/
│   ├── main.py      # Agent + tools (single file!)
│   └── db.py        # Database operations
├── frontend/        # (Add your frontend here)
├── requirements.txt
└── .env.example
```

## Tools Available

The agent has these function tools:

| Tool | Description |
|------|-------------|
| `lookup_user` | Identify user by phone number |
| `get_available_slots` | Show available appointment times |
| `book_appointment` | Book a new appointment |
| `get_my_appointments` | List user's appointments |
| `cancel_appointment` | Cancel an existing appointment |
| `end_call` | End call with summary |

## License

MIT

