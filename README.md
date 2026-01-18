# SuperBryn Voice Agent

A production-ready voice appointment booking system with AI assistant, full-screen Beyond Presence avatar, and comprehensive admin dashboard.

## 🎯 Features

### User Portal (`/`)
- Voice-based appointment booking with AI assistant
- **Full-screen Beyond Presence avatar** (via LiveKit BEY plugin)
- Real-time transcript display
- Tool call visualization
- Session history with status tags (Pending/Booked/Completed)
- End-of-call summary with cost breakdown

### Mentor Portal (`/mentor`)
- Outlook-style calendar view
- Appointment management
- Availability scheduling (add dates and time slots)
- View who has booked appointments

### Admin Portal (`/admin`)
- Dashboard with key metrics
- User management (view, add, delete)
- Mentor management
- Session viewer (full conversation history)
- Cost tracking and breakdown per session

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                          │
├──────────────────┬──────────────────┬──────────────────────────────┤
│    User Chat     │  Mentor Calendar │       Admin Dashboard         │
│  + LiveKit Room  │  + Availability  │  + Stats, Users, Sessions    │
│  + BEY Avatar    │  + Appointments  │  + Cost Tracking             │
└────────┬─────────┴────────┬─────────┴────────────┬─────────────────┘
         │                  │                      │
         │ WebRTC           │ REST API             │ REST API
         │ (video+audio)    │                      │
┌────────▼──────────────────▼──────────────────────▼─────────────────┐
│                         BACKEND                                      │
├─────────────────────────────┬───────────────────────────────────────┤
│    LiveKit Agent (main.py)  │        FastAPI (api.py)               │
│    - Deepgram STT           │        - Auth endpoints               │
│    - OpenAI LLM + Tools     │        - User/Mentor CRUD             │
│    - Cartesia TTS           │        - Appointments                 │
│    - BEY Avatar Plugin      │        - Sessions                     │
│    - Session tracking       │        - LiveKit tokens               │
└────────────────┬────────────┴───────────────────┬───────────────────┘
                 │                                │
                 └────────────────┬───────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      Supabase Database     │
                    │  - users, mentors, admins │
                    │  - appointments            │
                    │  - sessions, messages      │
                    │  - mentor_availability     │
                    └───────────────────────────┘
```

## 🚀 Quick Start

### 1. Database Setup

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. **Automatic Setup**: Add `SUPABASE_DB_PASSWORD` to `.env` - tables will be created automatically!
3. **Manual Setup**: Run `backend/schema.sql` in the SQL Editor
4. The backend automatically falls back to in-memory storage if tables don't exist

### 2. Backend Setup

```bash
# Create .env file in project root
cat > .env << EOF
# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# AI Services
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini

# Beyond Presence Avatar
BEY_API_KEY=your-beyond-presence-api-key
BEY_AVATAR_ID=1c7a7291-ee28-4800-8f34-acfbfc2d07c0

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_DB_PASSWORD=your-db-password  # Optional: enables auto table creation

# Auth
JWT_SECRET=your-jwt-secret-change-this
EOF

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
uv add livekit-agents[deepgram,cartesia,openai,silero,bey]
pip install -r requirements.txt

# Start API server (in one terminal)
cd backend && python api.py

# Start voice agent (in another terminal)
cd backend && python main.py start
```

### 3. Frontend Setup

```bash
cd frontend

# Create .env.local
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
EOF

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 4. Access

- **User Portal**: http://localhost:3000
- **Mentor Portal**: http://localhost:3000/mentor/login
- **Admin Portal**: http://localhost:3000/admin/login

**Default Credentials:**
- Mentor: `sarah@example.com` / `mentor123`
- Admin: `admin@superbryn.com` / `admin123`

## 🎭 Beyond Presence Avatar

The avatar is integrated using the **LiveKit BEY plugin**, not a frontend SDK. This means:

1. The avatar runs on the backend as a LiveKit participant
2. Video is streamed to the frontend via WebRTC
3. The avatar automatically syncs with TTS audio
4. Full-screen display with smooth video

**Setup:**
1. Get your API key from [app.bey.chat](https://app.bey.chat)
2. Get your avatar ID from [app.bey.chat/avatars](https://app.bey.chat/avatars)
3. Add to `.env`:
   ```
   BEY_API_KEY=your-api-key
   BEY_AVATAR_ID=1c7a7291-ee28-4800-8f34-acfbfc2d07c0
   ```

Reference: [LiveKit BEY Plugin Docs](https://docs.livekit.io/agents/models/avatar/plugins/bey/)

## 🔧 Troubleshooting

### Avatar Not Showing
- Verify `BEY_API_KEY` is set in `.env`
- Check agent logs for "Avatar started successfully" or error messages
- Ensure `BEY_AVATAR_ID` is a valid avatar from your account

### Database Errors
- The backend automatically falls back to in-memory storage
- Run `backend/schema.sql` in Supabase SQL Editor to create tables
- Continue using in-memory mode for testing

### LiveKit Connection Issues
- Verify `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` in `.env`
- Check that `NEXT_PUBLIC_LIVEKIT_URL` matches in frontend `.env.local`
- Ensure microphone permissions are granted in browser

## 📁 Project Structure

```
Voice-Agent/
├── backend/
│   ├── main.py          # LiveKit voice agent with BEY avatar
│   ├── api.py           # FastAPI REST endpoints
│   ├── db.py            # Database operations (with fallback)
│   └── schema.sql       # Supabase schema
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx           # User login
│       │   ├── chat/page.tsx      # Full-screen avatar chat
│       │   ├── mentor/            # Mentor dashboard
│       │   └── admin/             # Admin dashboard
│       ├── components/
│       │   └── LiveKitRoom.tsx    # LiveKit + avatar video
│       └── lib/
│           ├── api.ts             # API client
│           └── store.ts           # Zustand stores
├── requirements.txt
└── README.md
```

## 📝 License

MIT
