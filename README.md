# SuperBryn Voice Agent

A production-ready voice appointment booking system with AI assistant, visual avatar, and comprehensive admin dashboard.

## 🎯 Features

### User Portal (`/`)
- Voice-based appointment booking with AI assistant
- Visual avatar synced with speech (Beyond Presence)
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
│  + Avatar        │  + Appointments  │  + Cost Tracking             │
└────────┬─────────┴────────┬─────────┴────────────┬─────────────────┘
         │                  │                      │
         │ WebRTC           │ REST API             │ REST API
         │                  │                      │
┌────────▼──────────────────▼──────────────────────▼─────────────────┐
│                         BACKEND                                      │
├─────────────────────────────┬───────────────────────────────────────┤
│    LiveKit Agent (main.py)  │        FastAPI (api.py)               │
│    - Deepgram STT           │        - Auth endpoints               │
│    - OpenAI LLM + Tools     │        - User/Mentor CRUD             │
│    - Cartesia TTS           │        - Appointments                 │
│    - Session tracking       │        - Sessions                     │
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
                    │  - cost_logs              │
                    └───────────────────────────┘
```

## 🚀 Quick Start

### 1. Database Setup

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Run `backend/schema.sql` in the SQL Editor

### 2. Backend Setup

```bash
cd backend

# Create .env file
cat > .env << EOF
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
JWT_SECRET=your-jwt-secret-change-this
EOF

# Install dependencies
pip install -r ../requirements.txt

# Start API server
uvicorn api:app --reload --port 8000

# In another terminal, start voice agent
python main.py dev
```

### 3. Frontend Setup

```bash
cd frontend

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

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

## 📁 Project Structure

```
Voice-Agent/
├── backend/
│   ├── main.py          # LiveKit voice agent
│   ├── api.py           # FastAPI REST endpoints
│   ├── db.py            # Database operations
│   └── schema.sql       # Supabase schema
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx           # User login
│       │   ├── chat/page.tsx      # User chat interface
│       │   ├── mentor/
│       │   │   ├── login/page.tsx
│       │   │   └── page.tsx       # Mentor dashboard
│       │   └── admin/
│       │       ├── login/page.tsx
│       │       └── page.tsx       # Admin dashboard
│       └── lib/
│           ├── api.ts             # API client
│           └── store.ts           # Zustand stores
├── requirements.txt
└── README.md
```

## 🔧 API Endpoints

### Authentication
- `POST /api/auth/user/login` - User login (phone + name)
- `POST /api/auth/mentor/login` - Mentor login (email + password)
- `POST /api/auth/admin/login` - Admin login
- `GET /api/auth/me` - Get current user

### Users
- `GET /api/users` - List users (admin)
- `POST /api/users` - Create user (admin)
- `GET /api/users/{phone}/sessions` - User's sessions
- `GET /api/users/{phone}/appointments` - User's appointments

### Mentors
- `GET /api/mentors` - List mentors
- `POST /api/mentors` - Create mentor (admin)
- `GET /api/mentors/{id}/availability` - Get availability
- `POST /api/mentors/{id}/availability` - Add availability
- `GET /api/mentors/{id}/slots?date=YYYY-MM-DD` - Get slots for date

### Appointments
- `GET /api/appointments` - List appointments
- `GET /api/appointments/calendar` - Calendar view
- `PUT /api/appointments/{id}` - Update status/notes

### Sessions
- `GET /api/sessions` - List all sessions (admin)
- `GET /api/sessions/{id}` - Session with messages

### Admin
- `GET /api/admin/stats` - Dashboard statistics
- `GET /api/admin/costs` - Cost report
- `GET /api/admin/costs/sessions` - Per-session costs

### LiveKit
- `GET /api/livekit/token` - Get room token for voice chat

## 🤖 Voice Agent Tools

| Tool | Description |
|------|-------------|
| `identify_user` | Identify user by phone, load context |
| `fetch_slots` | Get available appointment slots |
| `book_appointment` | Book an appointment |
| `retrieve_appointments` | Get user's appointments |
| `cancel_appointment` | Cancel an appointment |
| `modify_appointment` | Reschedule appointment |
| `end_conversation` | End call with summary |

## 💰 Cost Tracking

The system tracks costs for:
- **Deepgram STT**: $0.0043/minute
- **Cartesia TTS**: $0.0015/100 characters
- **OpenAI GPT-4o-mini**: $0.00015/1K input, $0.0006/1K output

Costs are displayed at end of each call and aggregated in admin dashboard.

## 🔌 Beyond Presence Avatar Integration

To integrate Beyond Presence avatar:

1. Sign up at [beyondpresence.ai](https://beyondpresence.ai)
2. Get your API credentials
3. Replace the avatar placeholder in `frontend/src/app/chat/page.tsx`:

```tsx
// Replace the avatar container with Beyond Presence component
import { BeyondPresenceAvatar } from '@beyondpresence/react';

<BeyondPresenceAvatar
  apiKey={process.env.NEXT_PUBLIC_BP_API_KEY}
  avatarId="your-avatar-id"
  isSpeaking={isSpeaking}
  audioStream={audioStream}
/>
```

## 📝 License

MIT
