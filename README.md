<div align="center">

# 🎙️✨ Voice Agent - AI-Powered Appointment Booking System

**A production-ready voice appointment booking platform with AI assistant, full-screen avatar, and comprehensive admin dashboard**

[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![LiveKit](https://img.shields.io/badge/LiveKit-Agents-blue)](https://livekit.io/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org/)
[![Supabase](https://img.shields.io/badge/Supabase-Database-green)](https://supabase.com/)

**🚀 [Deploy on Railway](#-railway-deployment) | 📖 [User Flows](#-user-flows) | 🏗️ [Architecture](#-architecture)**

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [User Flows](#-user-flows)
- [Architecture](#-architecture)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)

---

## 🎯 Overview

Voice Agent is a complete appointment booking system that combines:
- **AI Voice Assistant** with natural conversation capabilities
- **Full-screen Beyond Presence Avatar** for visual interaction
- **Mentor Calendar Management** with Outlook-style interface
- **Admin Dashboard** with cost tracking and analytics

The system uses LiveKit Agents for real-time voice processing, OpenAI for intelligent conversation, and Supabase for data persistence.

---

## ✨ Features

### 👤 User Portal (`/chat`)
- 🎤 **Voice-based booking** - No typing required, just speak naturally
- 👤 **Full-screen AI Avatar** - Visual representation synced with speech
- 📝 **Real-time transcripts** - See what you and the AI said
- 🔧 **Tool call visualization** - Watch the AI book appointments in real-time
- 📚 **Session history** - View past conversations and appointments
- 📊 **Smart summaries** - Get a summary at the end of each call

### 👨‍⚕️ Mentor Portal (`/mentor`)
- 📅 **Outlook-style calendar** - Familiar day/week/month views
- ⏰ **Current time indicator** - Red line showing current time
- 📋 **Appointment management** - See who booked and when
- ✅ **Availability scheduling** - Add dates and time slots easily
- 📱 **Responsive design** - Works on all devices

### 👨‍💼 Admin Portal (`/admin`)
- 📊 **Dashboard analytics** - Key metrics at a glance
- 👥 **User management** - View, add, and manage users
- 👨‍⚕️ **Mentor management** - Create and manage mentors
- 💬 **Session viewer** - Full conversation history
- 💰 **Cost tracking** - Detailed cost breakdown per session (STT, TTS, LLM)
- 📈 **Usage statistics** - Track system usage and costs

---

## 🎭 User Flows

### Flow 1: User Booking an Appointment

```mermaid
graph TD
    A[User visits /chat] --> B[Click 'Start Voice Chat']
    B --> C[Avatar connects & loads]
    C --> D[AI greets user]
    D --> E[AI asks for phone number]
    E --> F[User provides phone number]
    F --> G[AI identifies/creates user]
    G --> H[AI asks what they need]
    H --> I[User: 'I want to book an appointment']
    I --> J[AI lists available mentors]
    J --> K[User selects mentor by name]
    K --> L[AI shows available time slots]
    L --> M[User picks date & time]
    M --> N[AI confirms booking]
    N --> O[Appointment saved to database]
    O --> P[AI provides summary]
    P --> Q[User sees appointment in sidebar]
```

**Key Steps:**
1. User enters `/chat` page
2. Clicks "Start Voice Chat" button
3. Waits for avatar to connect (with fun loader animation)
4. AI greets and asks for phone number
5. User provides phone number (voice-verified authentication)
6. AI loads user context (past appointments, sessions)
7. User requests appointment booking
8. AI lists mentors with specialties
9. User selects mentor
10. AI shows available slots for that mentor
11. User picks date/time
12. AI confirms and books appointment
13. Summary shown at end of conversation

### Flow 2: Mentor Managing Calendar

```mermaid
graph TD
    A[Mentor visits /mentor/login] --> B[Enters email & password]
    B --> C[Authenticated]
    C --> D[Sees Outlook-style calendar]
    D --> E[Views appointments for selected day]
    E --> F{Action?}
    F -->|Add Availability| G[Clicks '+ Add Availability']
    G --> H[Selects date & time range]
    H --> I[Saves availability]
    I --> J[Availability appears in sidebar]
    F -->|View Appointment| K[Clicks on appointment block]
    K --> L[Sees user details & notes]
    F -->|Navigate| M[Uses arrows to change date]
    M --> D
```

**Key Steps:**
1. Mentor logs in with email/password
2. Sees calendar with current time indicator (red line)
3. Views appointments as colored blocks on timeline
4. Can add availability via sidebar
5. Can navigate between days/weeks/months
6. Can see appointment details on hover/click

### Flow 3: Admin Monitoring System

```mermaid
graph TD
    A[Admin visits /admin/login] --> B[Enters credentials]
    B --> C[Authenticated]
    C --> D[Sees dashboard overview]
    D --> E{Action?}
    E -->|View Sessions| F[Clicks Sessions tab]
    F --> G[Sees all chat sessions]
    G --> H[Clicks session to view details]
    H --> I[Sees full conversation + cost]
    E -->|View Costs| J[Clicks Costs tab]
    J --> K[Sees cost breakdown by service]
    E -->|Add Mentor| L[Clicks Mentors tab]
    L --> M[Clicks '+ Add Mentor']
    M --> N[Fills form & creates]
    E -->|View Users| O[Clicks Users tab]
    O --> P[Sees all registered users]
```

**Key Steps:**
1. Admin logs in
2. Views dashboard with key metrics
3. Can view all sessions with full conversation history
4. Can see cost breakdown (STT, TTS, LLM) per session
5. Can add/manage mentors
6. Can view all users and their appointments

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                          │
│                         Deployed on Railway                         │
├──────────────────┬──────────────────┬──────────────────────────────┤
│    User Chat     │  Mentor Calendar │       Admin Dashboard         │
│  + LiveKit Room  │  + Availability  │  + Stats, Users, Sessions    │
│  + BEY Avatar    │  + Appointments  │  + Cost Tracking             │
│  (Full-screen)   │  (Outlook-style) │  (Analytics)                 │
└────────┬─────────┴────────┬─────────┴────────────┬─────────────────┘
         │                  │                      │
         │ WebRTC           │ REST API             │ REST API
         │ (video+audio)    │                      │
┌────────▼──────────────────▼──────────────────────▼─────────────────┐
│                         BACKEND                                      │
│                    (Separate Server/Cloud)                           │
├─────────────────────────────┬───────────────────────────────────────┤
│    LiveKit Agent (main.py)  │        FastAPI (api.py)               │
│    - Deepgram STT           │        - Auth endpoints               │
│    - OpenAI LLM + Tools     │        - User/Mentor CRUD             │
│    - Cartesia TTS           │        - Appointments                 │
│    - BEY Avatar Plugin      │        - Sessions                     │
│    - Session tracking       │        - LiveKit tokens               │
│    - Cost tracking          │        - Cost logs                    │
└────────────────┬────────────┴───────────────────┬───────────────────┘
                 │                                │
                 └────────────────┬───────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      Supabase Database     │
                    │  - users, mentors, admins │
                    │  - appointments            │
                    │  - sessions, messages      │
                    │  - mentor_availability        │
                    │  - cost_logs                │
                    └───────────────────────────┘
```

### Technology Stack

**Frontend:**
- Next.js 14 (React framework)
- Tailwind CSS (styling)
- LiveKit Client (WebRTC)
- Zustand (state management)

**Backend:**
- Python 3.12
- LiveKit Agents Framework
- FastAPI (REST API)
- Supabase (PostgreSQL database)

**AI Services:**
- Deepgram (Speech-to-Text)
- Cartesia (Text-to-Speech)
- OpenAI GPT-4o-mini (LLM)
- Beyond Presence (Avatar)


## 🔧 Troubleshooting

### Avatar Not Showing
- Verify `BEY_API_KEY` is set in `.env`
- Check agent logs for "Avatar started successfully" or error messages
- Ensure `BEY_AVATAR_ID` is a valid avatar from your account
- Check browser console for WebRTC connection errors

### Database Errors
- The backend automatically falls back to in-memory storage
- Run `backend/schema.sql` in Supabase SQL Editor to create tables
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check Supabase project is active

### LiveKit Connection Issues
- Verify `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` in `.env`
- Check that `NEXT_PUBLIC_LIVEKIT_URL` matches in frontend `.env.local`
- Ensure microphone permissions are granted in browser
- Check LiveKit Cloud dashboard for connection status

### Cost Tracking Shows $0
- Check backend logs for metrics collection messages
- Verify `metrics_collected` events are firing
- Ensure UsageCollector is properly initialized
- Check `cost_logs` table in Supabase for entries

### 401 Unauthorized Errors
- User endpoints now work without tokens (voice-verified users)
- Mentor/Admin endpoints require JWT tokens
- Check token expiration (24 hours default)
- Verify JWT_SECRET matches between backend instances

---

## 📁 Project Structure

```
Voice-Agent/
├── backend/
│   ├── main.py          # LiveKit voice agent with BEY avatar
│   ├── api.py           # FastAPI REST endpoints
│   ├── db.py            # Database operations (with fallback)
│   └── schema.sql       # Supabase schema
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Redirect to /chat
│   │   │   ├── chat/page.tsx      # Full-screen avatar chat
│   │   │   ├── mentor/            # Mentor dashboard
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── page.tsx
│   │   │   └── admin/             # Admin dashboard
│   │   │       ├── login/page.tsx
│   │   │       └── page.tsx
│   │   ├── components/
│   │   │   ├── LiveKitRoom.tsx    # LiveKit + avatar video
│   │   │   └── CallingLoader.tsx  # Loading animation
│   │   └── lib/
│   │       ├── api.ts             # API client
│   │       └── store.ts           # Zustand stores
│   ├── public/                    # Static assets
│   ├── .env.local                 # Frontend env vars
│   ├── next.config.js
│   └── package.json
├── .env                            # Backend env vars
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 📝 License

MIT License - feel free to use this project for your own purposes!

---

<div align="center">

**Built with ❤️ using LiveKit, Next.js, and OpenAI**

[Report Bug](https://github.com/your-repo/issues) · [Request Feature](https://github.com/your-repo/issues) · [Documentation](https://docs.livekit.io/)

</div>
