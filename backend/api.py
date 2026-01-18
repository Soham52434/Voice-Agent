"""
FastAPI Backend for Voice Agent
Provides REST API for frontend (users, mentors, admin, appointments)
"""
import os
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta, date, time
from typing import Optional, List
from functools import wraps

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (parent of backend directory)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Also try backend/.env
    load_dotenv(Path(__file__).parent / ".env")
    # And current directory
    load_dotenv()

from db import Database

logger = logging.getLogger(__name__)

# ==================== APP SETUP ====================

app = FastAPI(
    title="Voice Agent API",
    description="API for appointment booking voice agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()
security = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# ==================== PYDANTIC MODELS ====================

class UserLogin(BaseModel):
    phone: str = Field(..., min_length=10)
    name: str = Field(..., min_length=1)

class MentorLogin(BaseModel):
    email: str
    password: str

class AdminLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    token: str
    user_type: str
    user: dict

class UserCreate(BaseModel):
    contact_number: str
    name: str
    email: Optional[str] = None

class MentorCreate(BaseModel):
    name: str
    email: str
    password: str
    specialty: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None

class MentorUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class AvailabilityCreate(BaseModel):
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    slot_duration_minutes: int = 60

class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    mentor_notes: Optional[str] = None

# ==================== AUTH HELPERS ====================

def create_token(user_id: str, user_type: str, extra_data: dict = None) -> str:
    payload = {
        "sub": user_id,
        "type": user_type,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        **(extra_data or {})
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(token: dict = Depends(verify_token)) -> dict:
    if token.get("type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return token

def require_mentor(token: dict = Depends(verify_token)) -> dict:
    if token.get("type") != "mentor":
        raise HTTPException(status_code=403, detail="Mentor access required")
    return token

def require_user(token: dict = Depends(verify_token)) -> dict:
    if token.get("type") != "user":
        raise HTTPException(status_code=403, detail="User access required")
    return token

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ==================== AUTH ENDPOINTS ====================

@app.post("/api/auth/user/login", response_model=TokenResponse)
async def user_login(data: UserLogin):
    """Login/register as user with phone + name"""
    phone = "".join(filter(str.isdigit, data.phone))
    if len(phone) == 10:
        phone = f"+1{phone}"
    elif not phone.startswith("+"):
        phone = f"+{phone}"
    
    user = db.get_or_create_user(phone, data.name)
    
    # Update name if different
    if data.name != user.get("name"):
        db.update_user(phone, name=data.name)
        user["name"] = data.name
    
    token = create_token(phone, "user", {"name": user.get("name")})
    
    return {
        "token": token,
        "user_type": "user",
        "user": {
            "id": user.get("id"),
            "phone": phone,
            "name": user.get("name"),
        }
    }

@app.post("/api/auth/mentor/login", response_model=TokenResponse)
async def mentor_login(data: MentorLogin):
    """Login as mentor"""
    mentor = db.get_mentor_by_email(data.email)
    
    if not mentor:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, mentor.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(str(mentor["id"]), "mentor", {"name": mentor["name"]})
    
    return {
        "token": token,
        "user_type": "mentor",
        "user": {
            "id": mentor["id"],
            "name": mentor["name"],
            "email": mentor["email"],
            "specialty": mentor.get("specialty"),
        }
    }

@app.post("/api/auth/admin/login", response_model=TokenResponse)
async def admin_login(data: AdminLogin):
    """Login as admin"""
    admin = db.get_admin_by_email(data.email)
    
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, admin.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    db.update_admin_login(admin["id"])
    
    token = create_token(str(admin["id"]), "admin", {"role": admin.get("role")})
    
    return {
        "token": token,
        "user_type": "admin",
        "user": {
            "id": admin["id"],
            "name": admin["name"],
            "email": admin["email"],
            "role": admin.get("role"),
        }
    }

@app.get("/api/auth/me")
async def get_current_user(token: dict = Depends(verify_token)):
    """Get current authenticated user"""
    user_type = token.get("type")
    user_id = token.get("sub")
    
    if user_type == "user":
        user = db.get_or_create_user(user_id)
        return {"type": "user", "user": user}
    elif user_type == "mentor":
        mentor = db.get_mentor_by_id(user_id)
        return {"type": "mentor", "user": mentor}
    elif user_type == "admin":
        admin = db.get_admin_by_id(user_id)
        return {"type": "admin", "user": admin}
    
    raise HTTPException(status_code=401, detail="Invalid token type")

# ==================== USER ENDPOINTS ====================

@app.get("/api/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    token: dict = Depends(require_admin)
):
    """List all users (admin only)"""
    return db.list_users(skip=skip, limit=limit)

@app.post("/api/users")
async def create_user(data: UserCreate, token: dict = Depends(require_admin)):
    """Create a user (admin only)"""
    user = db.get_or_create_user(data.contact_number, data.name)
    if data.email:
        db.update_user(data.contact_number, email=data.email)
    return user

@app.get("/api/users/{phone}")
async def get_user(phone: str, token: dict = Depends(verify_token)):
    """Get user by phone"""
    user = db.get_user_by_phone(phone)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.delete("/api/users/{phone}")
async def delete_user(phone: str, token: dict = Depends(require_admin)):
    """Delete user (admin only)"""
    success = db.delete_user(phone)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

@app.get("/api/users/{phone}/sessions")
async def get_user_sessions(phone: str, token: dict = Depends(verify_token)):
    """Get user's chat sessions"""
    # Users can only see their own sessions
    if token.get("type") == "user" and token.get("sub") != phone:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        sessions = db.get_user_sessions(phone, limit=50)
        return sessions
    except Exception as e:
        # If database error, return empty list
        logger.error(f"Error fetching sessions: {e}")
        return []

@app.get("/api/users/{phone}/appointments")
async def get_user_appointments(
    phone: str,
    status: Optional[str] = None,
    token: dict = Depends(verify_token)
):
    """Get user's appointments"""
    if token.get("type") == "user" and token.get("sub") != phone:
        raise HTTPException(status_code=403, detail="Access denied")
    
    statuses = [status] if status else None
    appointments = db.get_user_appointments(phone, status=statuses)
    return appointments

# ==================== MENTOR ENDPOINTS ====================

@app.get("/api/mentors")
async def list_mentors(active_only: bool = True):
    """List all mentors"""
    return db.get_mentors(active_only=active_only)

@app.post("/api/mentors")
async def create_mentor(data: MentorCreate, token: dict = Depends(require_admin)):
    """Create a mentor (admin only)"""
    existing = db.get_mentor_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    mentor = db.create_mentor(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        specialty=data.specialty,
        bio=data.bio,
        phone=data.phone
    )
    return mentor

@app.get("/api/mentors/{mentor_id}")
async def get_mentor(mentor_id: str):
    """Get mentor details"""
    mentor = db.get_mentor_by_id(mentor_id)
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    # Remove sensitive data
    mentor.pop("password_hash", None)
    return mentor

@app.put("/api/mentors/{mentor_id}")
async def update_mentor(
    mentor_id: str,
    data: MentorUpdate,
    token: dict = Depends(verify_token)
):
    """Update mentor (mentor self or admin)"""
    if token.get("type") == "mentor" and token.get("sub") != mentor_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if token.get("type") not in ["mentor", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    mentor = db.update_mentor(mentor_id, **updates)
    return mentor

@app.delete("/api/mentors/{mentor_id}")
async def delete_mentor(mentor_id: str, token: dict = Depends(require_admin)):
    """Delete mentor (admin only)"""
    success = db.delete_mentor(mentor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mentor not found")
    return {"message": "Mentor deleted"}

# ==================== MENTOR AVAILABILITY ENDPOINTS ====================

@app.get("/api/mentors/{mentor_id}/availability")
async def get_mentor_availability(
    mentor_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get mentor's availability"""
    return db.get_mentor_availability(mentor_id, start_date, end_date)

@app.post("/api/mentors/{mentor_id}/availability")
async def add_mentor_availability(
    mentor_id: str,
    data: AvailabilityCreate,
    token: dict = Depends(require_mentor)
):
    """Add availability slot (mentor only)"""
    if token.get("sub") != mentor_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    availability = db.add_mentor_availability(
        mentor_id=mentor_id,
        date_str=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        slot_duration=data.slot_duration_minutes
    )
    return availability

@app.delete("/api/mentors/{mentor_id}/availability/{availability_id}")
async def remove_mentor_availability(
    mentor_id: str,
    availability_id: str,
    token: dict = Depends(require_mentor)
):
    """Remove availability slot"""
    if token.get("sub") != mentor_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = db.remove_mentor_availability(availability_id)
    if not success:
        raise HTTPException(status_code=404, detail="Availability not found")
    return {"message": "Availability removed"}

@app.get("/api/mentors/{mentor_id}/slots")
async def get_mentor_slots(
    mentor_id: str,
    date: str
):
    """Get available booking slots for a mentor on a date"""
    return db.get_available_slots_for_mentor(mentor_id, date)

# ==================== APPOINTMENT ENDPOINTS ====================

@app.get("/api/appointments")
async def list_appointments(
    status: Optional[str] = None,
    mentor_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token: dict = Depends(verify_token)
):
    """List appointments (filtered based on user type)"""
    user_type = token.get("type")
    
    if user_type == "user":
        phone = token.get("sub")
        return db.get_user_appointments(phone, status=status)
    elif user_type == "mentor":
        m_id = token.get("sub")
        return db.get_mentor_appointments(m_id, status, start_date, end_date)
    elif user_type == "admin":
        return db.list_all_appointments(status, mentor_id, start_date, end_date)
    
    raise HTTPException(status_code=403, detail="Access denied")

@app.get("/api/appointments/calendar")
async def get_appointments_calendar(
    mentor_id: str,
    month: int,
    year: int,
    token: dict = Depends(verify_token)
):
    """Get calendar view of appointments for a mentor"""
    if token.get("type") == "mentor" and token.get("sub") != mentor_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return db.get_mentor_calendar(mentor_id, year, month)

@app.get("/api/appointments/{appointment_id}")
async def get_appointment(appointment_id: str, token: dict = Depends(verify_token)):
    """Get appointment details"""
    appointment = db.get_appointment_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check access
    user_type = token.get("type")
    if user_type == "user" and appointment.get("contact_number") != token.get("sub"):
        raise HTTPException(status_code=403, detail="Access denied")
    if user_type == "mentor" and str(appointment.get("mentor_id")) != token.get("sub"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return appointment

@app.put("/api/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    data: AppointmentUpdate,
    token: dict = Depends(verify_token)
):
    """Update appointment status or notes"""
    appointment = db.get_appointment_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    updated = db.update_appointment(appointment_id, **updates)
    return updated

# ==================== SESSION ENDPOINTS ====================

@app.get("/api/sessions")
async def list_sessions(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    token: dict = Depends(require_admin)
):
    """List all sessions (admin only)"""
    return db.list_all_sessions(status=status, skip=skip, limit=limit)

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, token: dict = Depends(verify_token)):
    """Get session details with messages"""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check access for non-admins
    if token.get("type") == "user" and session.get("contact_number") != token.get("sub"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = db.get_session_messages(session_id)
    return {
        "session": session,
        "messages": messages
    }

# ==================== ADMIN ENDPOINTS ====================

@app.get("/api/admin/stats")
async def get_admin_stats(token: dict = Depends(require_admin)):
    """Get dashboard statistics"""
    return db.get_admin_stats()

@app.get("/api/admin/costs")
async def get_cost_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day",  # day, week, month
    token: dict = Depends(require_admin)
):
    """Get cost breakdown"""
    return db.get_cost_report(start_date, end_date, group_by)

@app.get("/api/admin/costs/sessions")
async def get_session_costs(
    skip: int = 0,
    limit: int = 50,
    token: dict = Depends(require_admin)
):
    """Get per-session cost breakdown"""
    return db.get_session_costs(skip=skip, limit=limit)

# ==================== LIVEKIT TOKEN ENDPOINT ====================

@app.get("/api/livekit/token")
async def get_livekit_token(token: dict = Depends(require_user)):
    """Get LiveKit room token for voice chat"""
    try:
        from livekit import api as livekit_api
        
        user_phone = token.get("sub")
        user_name = token.get("name", "User")
        
        # Create unique room name
        room_name = f"voice-{user_phone.replace('+', '')}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Generate LiveKit token
        livekit_url = os.getenv("LIVEKIT_URL")
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")
        
        if not all([livekit_url, api_key, api_secret]):
            raise HTTPException(status_code=500, detail="LiveKit configuration missing")
        
        token_opts = livekit_api.VideoGrants(
            room_join=True,
            room=room_name,
        )
        
        participant_token = livekit_api.AccessToken(
            api_key,
            api_secret
        ).with_identity(user_phone).with_name(user_name).with_grants(token_opts).to_jwt()
        
        return {
            "token": participant_token,
            "room_name": room_name,
            "livekit_url": livekit_url
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="LiveKit API not installed. Install: pip install livekit-api")
    except Exception as e:
        logger.error(f"Failed to generate LiveKit token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")

# ==================== HEALTH CHECK ====================

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/db/status")
async def db_status():
    """Check database connection status."""
    status = {
        "enabled": db._enabled,
        "using_supabase": db._enabled and db.client is not None,
        "using_memory": not db._enabled,
        "supabase_url_set": bool(os.getenv("SUPABASE_URL")),
        "supabase_key_set": bool(os.getenv("SUPABASE_KEY")),
    }
    
    if db._enabled and db.client:
        try:
            # Try a simple query to verify connection
            db.client.table("users").select("id").limit(1).execute()
            status["connection_test"] = "success"
            status["message"] = "Connected to Supabase"
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                status["connection_test"] = "tables_missing"
                status["message"] = "Connected but tables not found. Run backend/schema.sql in Supabase."
            else:
                status["connection_test"] = "failed"
                status["message"] = f"Connection error: {error_msg}"
    else:
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
            status["message"] = "SUPABASE_URL and/or SUPABASE_KEY not set in .env"
        else:
            status["message"] = "Using in-memory storage"
    
    return status

# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

