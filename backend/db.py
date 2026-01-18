"""
Database operations for Voice Agent.
Handles users, mentors, appointments, sessions, and admin operations.
"""
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from dotenv import load_dotenv

load_dotenv()


class Database:
    """Supabase database wrapper with full functionality."""
    
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if url and key:
            from supabase import create_client
            self.client = create_client(url, key)
            self._enabled = True
        else:
            print("⚠️  Supabase not configured - using in-memory storage")
            self.client = None
            self._enabled = False
            self._init_memory_storage()
    
    def _init_memory_storage(self):
        """Initialize in-memory storage for testing."""
        self._users: dict[str, dict] = {}
        self._mentors: dict[str, dict] = {
            "1": {"id": "1", "name": "Dr. Sarah Smith", "email": "sarah@example.com", 
                  "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qVYHJqI/4p4J1C",  # mentor123
                  "specialty": "General Consultation", "is_active": True},
            "2": {"id": "2", "name": "Dr. John Doe", "email": "john@example.com",
                  "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qVYHJqI/4p4J1C",
                  "specialty": "Technical Review", "is_active": True},
        }
        self._admins: dict[str, dict] = {
            "1": {"id": "1", "name": "Super Admin", "email": "admin@superbryn.com",
                  "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qVYHJqI/4p4J1C",  # admin123
                  "role": "super_admin", "is_active": True}
        }
        self._appointments: list[dict] = []
        self._sessions: dict[str, dict] = {}
        self._messages: list[dict] = []
        self._availability: list[dict] = []
        self._cost_logs: list[dict] = []
    
    # ==================== USERS ====================
    
    def get_or_create_user(self, phone: str, name: str = "User") -> dict[str, Any]:
        """Get existing user or create new one."""
        if not self._enabled:
            if phone not in self._users:
                self._users[phone] = {
                    "id": phone,
                    "contact_number": phone,
                    "name": name,
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                }
            return self._users[phone]
        
        response = self.client.table("users").select("*").eq("contact_number", phone).execute()
        
        if response.data:
            return response.data[0]
        
        user_data = {
            "contact_number": phone,
            "name": name,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
        }
        response = self.client.table("users").insert(user_data).execute()
        return response.data[0] if response.data else user_data
    
    def get_user_by_phone(self, phone: str) -> dict[str, Any] | None:
        """Get user by phone number."""
        if not self._enabled:
            return self._users.get(phone)
        
        response = self.client.table("users").select("*").eq("contact_number", phone).execute()
        return response.data[0] if response.data else None
    
    def update_user(self, phone: str, **kwargs) -> dict[str, Any]:
        """Update user details."""
        kwargs["updated_at"] = datetime.now().isoformat()
        
        if not self._enabled:
            if phone in self._users:
                self._users[phone].update(kwargs)
            return self._users.get(phone, {})
        
        response = self.client.table("users").update(kwargs).eq("contact_number", phone).execute()
        return response.data[0] if response.data else {}
    
    def list_users(self, skip: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        """List all users."""
        if not self._enabled:
            users = list(self._users.values())
            return users[skip:skip + limit]
        
        response = self.client.table("users").select("*").range(skip, skip + limit - 1).execute()
        return response.data or []
    
    def delete_user(self, phone: str) -> bool:
        """Delete a user."""
        if not self._enabled:
            if phone in self._users:
                del self._users[phone]
                return True
            return False
        
        response = self.client.table("users").delete().eq("contact_number", phone).execute()
        return bool(response.data)
    
    # ==================== MENTORS ====================
    
    def get_mentors(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Get all mentors."""
        if not self._enabled:
            mentors = list(self._mentors.values())
            if active_only:
                mentors = [m for m in mentors if m.get("is_active")]
            for m in mentors:
                m.pop("password_hash", None)
            return mentors
        
        query = self.client.table("mentors").select("id, name, email, specialty, bio, phone, avatar_url, is_active, created_at")
        if active_only:
            query = query.eq("is_active", True)
        response = query.execute()
        return response.data or []
    
    def get_mentor_by_id(self, mentor_id: str) -> dict[str, Any] | None:
        """Get mentor by ID."""
        if not self._enabled:
            mentor = self._mentors.get(mentor_id)
            if mentor:
                return {k: v for k, v in mentor.items() if k != "password_hash"}
            return None
        
        response = self.client.table("mentors").select("*").eq("id", mentor_id).execute()
        if response.data:
            mentor = response.data[0]
            mentor.pop("password_hash", None)
            return mentor
        return None
    
    def get_mentor_by_email(self, email: str) -> dict[str, Any] | None:
        """Get mentor by email (includes password_hash for auth)."""
        if not self._enabled:
            for m in self._mentors.values():
                if m.get("email") == email:
                    return m
            return None
        
        response = self.client.table("mentors").select("*").eq("email", email).execute()
        return response.data[0] if response.data else None
    
    def create_mentor(self, name: str, email: str, password_hash: str, 
                      specialty: str = None, bio: str = None, phone: str = None) -> dict[str, Any]:
        """Create a new mentor."""
        mentor_data = {
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "specialty": specialty,
            "bio": bio,
            "phone": phone,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
        
        if not self._enabled:
            mentor_id = str(len(self._mentors) + 1)
            mentor_data["id"] = mentor_id
            self._mentors[mentor_id] = mentor_data
            return {k: v for k, v in mentor_data.items() if k != "password_hash"}
        
        response = self.client.table("mentors").insert(mentor_data).execute()
        if response.data:
            mentor = response.data[0]
            mentor.pop("password_hash", None)
            return mentor
        return {}
    
    def update_mentor(self, mentor_id: str, **kwargs) -> dict[str, Any]:
        """Update mentor details."""
        kwargs["updated_at"] = datetime.now().isoformat()
        
        if not self._enabled:
            if mentor_id in self._mentors:
                self._mentors[mentor_id].update(kwargs)
                return {k: v for k, v in self._mentors[mentor_id].items() if k != "password_hash"}
            return {}
        
        response = self.client.table("mentors").update(kwargs).eq("id", mentor_id).execute()
        if response.data:
            mentor = response.data[0]
            mentor.pop("password_hash", None)
            return mentor
        return {}
    
    def delete_mentor(self, mentor_id: str) -> bool:
        """Delete a mentor."""
        if not self._enabled:
            if mentor_id in self._mentors:
                del self._mentors[mentor_id]
                return True
            return False
        
        response = self.client.table("mentors").delete().eq("id", mentor_id).execute()
        return bool(response.data)
    
    # ==================== MENTOR AVAILABILITY ====================
    
    def get_mentor_availability(self, mentor_id: str, start_date: str = None, end_date: str = None) -> list[dict]:
        """Get mentor's availability."""
        if not self._enabled:
            avail = [a for a in self._availability if a.get("mentor_id") == mentor_id]
            if start_date:
                avail = [a for a in avail if a.get("date") >= start_date]
            if end_date:
                avail = [a for a in avail if a.get("date") <= end_date]
            return avail
        
        query = self.client.table("mentor_availability").select("*").eq("mentor_id", mentor_id)
        if start_date:
            query = query.gte("date", start_date)
        if end_date:
            query = query.lte("date", end_date)
        response = query.order("date").execute()
        return response.data or []
    
    def add_mentor_availability(self, mentor_id: str, date_str: str, 
                                start_time: str, end_time: str, slot_duration: int = 60) -> dict:
        """Add availability for a mentor."""
        avail_data = {
            "mentor_id": mentor_id,
            "date": date_str,
            "start_time": start_time,
            "end_time": end_time,
            "slot_duration_minutes": slot_duration,
            "is_available": True,
            "created_at": datetime.now().isoformat()
        }
        
        if not self._enabled:
            avail_data["id"] = f"avail_{len(self._availability) + 1}"
            self._availability.append(avail_data)
            return avail_data
        
        response = self.client.table("mentor_availability").insert(avail_data).execute()
        return response.data[0] if response.data else avail_data
    
    def remove_mentor_availability(self, availability_id: str) -> bool:
        """Remove availability slot."""
        if not self._enabled:
            self._availability = [a for a in self._availability if a.get("id") != availability_id]
            return True
        
        response = self.client.table("mentor_availability").delete().eq("id", availability_id).execute()
        return bool(response.data)
    
    def get_available_slots_for_mentor(self, mentor_id: str, date_str: str) -> list[dict]:
        """Get available time slots for a mentor on a specific date."""
        availability = self.get_mentor_availability(mentor_id, start_date=date_str, end_date=date_str)
        
        if not availability:
            return []
        
        avail = availability[0]
        start_time = datetime.strptime(avail["start_time"], "%H:%M")
        end_time = datetime.strptime(avail["end_time"], "%H:%M")
        slot_duration = avail.get("slot_duration_minutes", 60)
        
        slots = []
        current = start_time
        
        while current < end_time:
            time_str = current.strftime("%H:%M")
            is_booked = self.is_slot_booked(date_str, time_str, mentor_id)
            slots.append({
                "time": time_str,
                "is_booked": is_booked,
                "available": not is_booked
            })
            current += timedelta(minutes=slot_duration)
        
        return slots
    
    # ==================== APPOINTMENTS ====================
    
    def is_slot_booked(self, date_str: str, time_str: str, mentor_id: str = None) -> bool:
        """Check if a slot is already booked."""
        if not self._enabled:
            return any(
                apt["date"] == date_str and 
                apt["time"] == time_str and 
                apt["status"] in ("pending", "booked") and
                (mentor_id is None or apt.get("mentor_id") == mentor_id)
                for apt in self._appointments
            )
        
        query = self.client.table("appointments").select("id").eq("date", date_str).eq("time", time_str).in_("status", ["pending", "booked"])
        if mentor_id:
            query = query.eq("mentor_id", mentor_id)
        response = query.execute()
        return bool(response.data)
    
    def book_appointment(self, phone: str, date_str: str, time_str: str,
                         mentor_id: str = None, notes: str = None) -> dict[str, Any]:
        """Book a new appointment."""
        user = self.get_or_create_user(phone)
        
        apt_data = {
            "user_id": user.get("id"),
            "contact_number": phone,
            "date": date_str,
            "time": time_str,
            "status": "booked",
            "mentor_id": mentor_id,
            "notes": notes,
            "created_at": datetime.now().isoformat(),
        }
        
        if not self._enabled:
            apt_data["id"] = f"apt_{len(self._appointments) + 1}"
            self._appointments.append(apt_data)
            return apt_data
        
        response = self.client.table("appointments").insert(apt_data).execute()
        return response.data[0] if response.data else apt_data
    
    def get_user_appointments(self, phone: str, status: list[str] | str = None) -> list[dict[str, Any]]:
        """Get appointments for a user."""
        if not self._enabled:
            results = [apt for apt in self._appointments if apt["contact_number"] == phone]
            if status:
                statuses = [status] if isinstance(status, str) else status
                results = [apt for apt in results if apt["status"] in statuses]
            return sorted(results, key=lambda x: (x["date"], x["time"]))
        
        query = self.client.table("appointments").select("*, mentors(name, specialty)").eq("contact_number", phone)
        if status:
            if isinstance(status, str):
                query = query.eq("status", status)
            else:
                query = query.in_("status", status)
        response = query.order("date").order("time").execute()
        return response.data or []
    
    def get_mentor_appointments(self, mentor_id: str, status: str = None,
                                start_date: str = None, end_date: str = None) -> list[dict]:
        """Get appointments for a mentor."""
        if not self._enabled:
            results = [apt for apt in self._appointments if apt.get("mentor_id") == mentor_id]
            if status:
                results = [apt for apt in results if apt["status"] == status]
            if start_date:
                results = [apt for apt in results if apt["date"] >= start_date]
            if end_date:
                results = [apt for apt in results if apt["date"] <= end_date]
            return results
        
        query = self.client.table("appointments").select("*, users(name, contact_number)").eq("mentor_id", mentor_id)
        if status:
            query = query.eq("status", status)
        if start_date:
            query = query.gte("date", start_date)
        if end_date:
            query = query.lte("date", end_date)
        response = query.order("date").order("time").execute()
        return response.data or []
    
    def get_mentor_calendar(self, mentor_id: str, year: int, month: int) -> dict:
        """Get calendar view for a mentor."""
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        appointments = self.get_mentor_appointments(mentor_id, start_date=start_date, end_date=end_date)
        availability = self.get_mentor_availability(mentor_id, start_date=start_date, end_date=end_date)
        
        # Group by date
        calendar = {}
        for apt in appointments:
            date = apt["date"]
            if date not in calendar:
                calendar[date] = {"appointments": [], "availability": None}
            calendar[date]["appointments"].append(apt)
        
        for avail in availability:
            date = avail["date"]
            if date not in calendar:
                calendar[date] = {"appointments": [], "availability": None}
            calendar[date]["availability"] = avail
        
        return {
            "year": year,
            "month": month,
            "days": calendar
        }
    
    def get_appointment_by_id(self, appointment_id: str) -> dict | None:
        """Get appointment by ID."""
        if not self._enabled:
            for apt in self._appointments:
                if apt.get("id") == appointment_id:
                    return apt
            return None
        
        response = self.client.table("appointments").select("*, users(name, contact_number), mentors(name, specialty)").eq("id", appointment_id).execute()
        return response.data[0] if response.data else None
    
    def update_appointment(self, appointment_id: str, **kwargs) -> dict:
        """Update appointment."""
        kwargs["updated_at"] = datetime.now().isoformat()
        
        if not self._enabled:
            for apt in self._appointments:
                if apt.get("id") == appointment_id:
                    apt.update(kwargs)
                    return apt
            return {}
        
        response = self.client.table("appointments").update(kwargs).eq("id", appointment_id).execute()
        return response.data[0] if response.data else {}
    
    def cancel_appointment(self, phone: str, date_str: str, time_str: str) -> bool:
        """Cancel an appointment."""
        if not self._enabled:
            for apt in self._appointments:
                if (apt["contact_number"] == phone and apt["date"] == date_str and 
                    apt["time"] == time_str and apt["status"] in ("pending", "booked")):
                    apt["status"] = "cancelled"
                    apt["updated_at"] = datetime.now().isoformat()
                    return True
            return False
        
        response = self.client.table("appointments").update({
            "status": "cancelled", 
            "updated_at": datetime.now().isoformat()
        }).eq("contact_number", phone).eq("date", date_str).eq("time", time_str).in_("status", ["pending", "booked"]).execute()
        return bool(response.data)
    
    def modify_appointment(self, phone: str, old_date: str, old_time: str,
                           new_date: str, new_time: str) -> dict | None:
        """Modify appointment date/time."""
        if self.is_slot_booked(new_date, new_time):
            return None
        
        if not self._enabled:
            for apt in self._appointments:
                if (apt["contact_number"] == phone and apt["date"] == old_date and 
                    apt["time"] == old_time and apt["status"] in ("pending", "booked")):
                    apt["date"] = new_date
                    apt["time"] = new_time
                    apt["updated_at"] = datetime.now().isoformat()
                    return apt
            return None
        
        response = self.client.table("appointments").update({
            "date": new_date,
            "time": new_time,
            "updated_at": datetime.now().isoformat()
        }).eq("contact_number", phone).eq("date", old_date).eq("time", old_time).in_("status", ["pending", "booked"]).execute()
        return response.data[0] if response.data else None
    
    def list_all_appointments(self, status: str = None, mentor_id: str = None,
                              start_date: str = None, end_date: str = None) -> list[dict]:
        """List all appointments (admin)."""
        if not self._enabled:
            results = self._appointments.copy()
            if status:
                results = [a for a in results if a["status"] == status]
            if mentor_id:
                results = [a for a in results if a.get("mentor_id") == mentor_id]
            if start_date:
                results = [a for a in results if a["date"] >= start_date]
            if end_date:
                results = [a for a in results if a["date"] <= end_date]
            return results
        
        query = self.client.table("appointments").select("*, users(name, contact_number), mentors(name, specialty)")
        if status:
            query = query.eq("status", status)
        if mentor_id:
            query = query.eq("mentor_id", mentor_id)
        if start_date:
            query = query.gte("date", start_date)
        if end_date:
            query = query.lte("date", end_date)
        response = query.order("date", desc=True).order("time").execute()
        return response.data or []
    
    # ==================== SESSIONS ====================
    
    def create_session(self, room_name: str, contact_number: str = None) -> dict[str, Any]:
        """Create a new session."""
        session_data = {
            "room_name": room_name,
            "contact_number": contact_number,
            "started_at": datetime.now().isoformat(),
            "status": "active",
            "metadata": {}
        }
        
        if not self._enabled:
            session_id = f"session_{len(self._sessions) + 1}"
            session_data["id"] = session_id
            self._sessions[session_id] = session_data
            return session_data
        
        response = self.client.table("sessions").insert(session_data).execute()
        return response.data[0] if response.data else session_data
    
    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID."""
        if not self._enabled:
            return self._sessions.get(session_id)
        
        response = self.client.table("sessions").select("*").eq("id", session_id).execute()
        return response.data[0] if response.data else None
    
    def update_session(self, session_id: str, **kwargs) -> None:
        """Update session."""
        if not self._enabled:
            if session_id in self._sessions:
                self._sessions[session_id].update(kwargs)
            return
        
        self.client.table("sessions").update(kwargs).eq("id", session_id).execute()
    
    def link_session_to_user(self, session_id: str, phone: str) -> None:
        """Link session to user."""
        user = self.get_or_create_user(phone)
        self.update_session(session_id, contact_number=phone, user_id=user.get("id"))
    
    def end_session(self, session_id: str, contact_number: str = None,
                    summary: str = None, cost_breakdown: dict = None) -> None:
        """End a session."""
        update_data = {
            "ended_at": datetime.now().isoformat(),
            "status": "completed"
        }
        if contact_number:
            update_data["contact_number"] = contact_number
        if summary:
            update_data["summary"] = summary
        if cost_breakdown:
            update_data["cost_breakdown"] = cost_breakdown
        
        # Calculate duration
        session = self.get_session(session_id)
        if session and session.get("started_at"):
            started = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
            ended = datetime.now()
            update_data["duration_seconds"] = int((ended - started).total_seconds())
        
        self.update_session(session_id, **update_data)
    
    def add_message(self, session_id: str, role: str, content: str,
                    tool_name: str = None, tool_args: dict = None, tool_result: dict = None) -> dict:
        """Add message to session."""
        msg_data = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result,
            "timestamp": datetime.now().isoformat()
        }
        
        if not self._enabled:
            msg_data["id"] = f"msg_{len(self._messages) + 1}"
            self._messages.append(msg_data)
            return msg_data
        
        response = self.client.table("session_messages").insert(msg_data).execute()
        return response.data[0] if response.data else msg_data
    
    def get_session_messages(self, session_id: str) -> list[dict]:
        """Get all messages for a session."""
        if not self._enabled:
            return [m for m in self._messages if m["session_id"] == session_id]
        
        response = self.client.table("session_messages").select("*").eq("session_id", session_id).order("timestamp").execute()
        return response.data or []
    
    def get_user_sessions(self, phone: str, limit: int = 50) -> list[dict]:
        """Get user's sessions."""
        if not self._enabled:
            sessions = [s for s in self._sessions.values() if s.get("contact_number") == phone]
            return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)[:limit]
        
        response = self.client.table("sessions").select("*").eq("contact_number", phone).order("started_at", desc=True).limit(limit).execute()
        return response.data or []
    
    def list_all_sessions(self, status: str = None, skip: int = 0, limit: int = 50) -> list[dict]:
        """List all sessions (admin)."""
        if not self._enabled:
            sessions = list(self._sessions.values())
            if status:
                sessions = [s for s in sessions if s.get("status") == status]
            return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)[skip:skip + limit]
        
        query = self.client.table("sessions").select("*, users(name)")
        if status:
            query = query.eq("status", status)
        response = query.order("started_at", desc=True).range(skip, skip + limit - 1).execute()
        return response.data or []
    
    # ==================== CONTEXT RETRIEVAL ====================
    
    def get_user_context(self, phone: str) -> dict[str, Any]:
        """Get comprehensive context for a user."""
        user = self.get_or_create_user(phone)
        
        booked = self.get_user_appointments(phone, status=["booked"])
        pending = self.get_user_appointments(phone, status=["pending"])
        completed = self.get_user_appointments(phone, status=["completed"])
        cancelled = self.get_user_appointments(phone, status=["cancelled"])
        
        sessions = self.get_user_sessions(phone, limit=5)
        last_session = sessions[0] if sessions else None
        
        return {
            "user": user,
            "is_returning": len(sessions) > 0,
            "total_sessions": len(sessions),
            "appointments": {
                "booked": booked,
                "pending": pending,
                "completed_count": len(completed),
                "cancelled_count": len(cancelled),
            },
            "last_session": {
                "date": last_session.get("started_at") if last_session else None,
                "summary": last_session.get("summary") if last_session else None,
            },
            "recent_conversation_snippets": []
        }
    
    def format_context_for_agent(self, context: dict[str, Any]) -> str:
        """Format user context for agent."""
        if not context.get("is_returning"):
            return ""
        
        parts = [f"RETURNING USER: {context['user'].get('name', 'Unknown')}"]
        
        booked = context.get("appointments", {}).get("booked", [])
        if booked:
            parts.append(f"Upcoming appointments: {len(booked)}")
            for apt in booked[:3]:
                parts.append(f"  - {apt.get('date')} at {apt.get('time')}")
        
        last = context.get("last_session", {})
        if last.get("summary"):
            parts.append(f"Last conversation: {last.get('summary')}")
        
        return "\n".join(parts)
    
    # ==================== ADMINS ====================
    
    def get_admin_by_email(self, email: str) -> dict | None:
        """Get admin by email."""
        if not self._enabled:
            for admin in self._admins.values():
                if admin.get("email") == email:
                    return admin
            return None
        
        response = self.client.table("admins").select("*").eq("email", email).execute()
        return response.data[0] if response.data else None
    
    def get_admin_by_id(self, admin_id: str) -> dict | None:
        """Get admin by ID."""
        if not self._enabled:
            admin = self._admins.get(admin_id)
            if admin:
                return {k: v for k, v in admin.items() if k != "password_hash"}
            return None
        
        response = self.client.table("admins").select("id, name, email, role, is_active, created_at, last_login").eq("id", admin_id).execute()
        return response.data[0] if response.data else None
    
    def update_admin_login(self, admin_id: str) -> None:
        """Update admin last login time."""
        if not self._enabled:
            if admin_id in self._admins:
                self._admins[admin_id]["last_login"] = datetime.now().isoformat()
            return
        
        self.client.table("admins").update({"last_login": datetime.now().isoformat()}).eq("id", admin_id).execute()
    
    def get_admin_stats(self) -> dict:
        """Get admin dashboard statistics."""
        if not self._enabled:
            return {
                "total_users": len(self._users),
                "total_mentors": len([m for m in self._mentors.values() if m.get("is_active")]),
                "total_sessions": len(self._sessions),
                "active_sessions": len([s for s in self._sessions.values() if s.get("status") == "active"]),
                "total_appointments": len(self._appointments),
                "pending_appointments": len([a for a in self._appointments if a["status"] == "pending"]),
                "booked_appointments": len([a for a in self._appointments if a["status"] == "booked"]),
                "completed_appointments": len([a for a in self._appointments if a["status"] == "completed"]),
                "total_cost": sum(c.get("cost_usd", 0) for c in self._cost_logs)
            }
        
        # Use SQL function
        response = self.client.rpc("get_admin_stats").execute()
        if response.data:
            return response.data[0]
        return {}
    
    def get_cost_report(self, start_date: str = None, end_date: str = None, group_by: str = "day") -> list[dict]:
        """Get cost report."""
        if not self._enabled:
            return []
        
        response = self.client.from_("cost_summary").select("*").execute()
        return response.data or []
    
    def get_session_costs(self, skip: int = 0, limit: int = 50) -> list[dict]:
        """Get per-session costs."""
        if not self._enabled:
            sessions = list(self._sessions.values())
            for s in sessions:
                s["cost"] = s.get("cost_breakdown", {}).get("total", 0)
            return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)[skip:skip + limit]
        
        response = self.client.table("sessions").select("id, room_name, contact_number, started_at, ended_at, duration_seconds, summary, cost_breakdown, users(name)").order("started_at", desc=True).range(skip, skip + limit - 1).execute()
        return response.data or []
