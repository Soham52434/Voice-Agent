"""
Database operations for Voice Agent.
Simplified with Supabase + in-memory fallback.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Any
from pathlib import Path

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path) if env_path.exists() else load_dotenv()

logger = logging.getLogger(__name__)


class Database:
    """Supabase database with automatic in-memory fallback."""
    
    def __init__(self):
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_KEY", "").strip()
        
        self.client = None
        self._enabled = False
        self._init_memory()
        
        if url and key and url.startswith("https://") and ".supabase.co" in url:
            try:
                from supabase import create_client
                print(f"🔗 Connecting to Supabase at {url}...")
                self.client = create_client(url, key)
                # Test connection
                self.client.table("users").select("id").limit(1).execute()
                print("✅ Successfully connected to Supabase!")
                self._enabled = True
            except Exception as e:
                print(f"⚠️  Supabase connection failed: {e}")
                print("   Using in-memory storage")
    
    def _init_memory(self):
        """Initialize in-memory storage."""
        self._users: dict = {}
        self._mentors: dict = {
            "1": {"id": "1", "name": "Dr. Sarah Smith", "specialty": "General Consultation", "is_active": True},
            "2": {"id": "2", "name": "Dr. John Doe", "specialty": "Technical Review", "is_active": True},
        }
        self._appointments: list = []
        self._sessions: dict = {}
        self._messages: list = []
        self._availability: list = []
    
    def _db(self, supabase_fn, memory_fn):
        """Execute Supabase query with memory fallback."""
        if self._enabled:
            try:
                return supabase_fn()
            except Exception:
                pass
        return memory_fn()
    
    # ==================== USERS ====================
    
    def get_or_create_user(self, phone: str, name: str = "User") -> dict:
        """Get existing user or create new one."""
        def from_db():
            res = self.client.table("users").select("*").eq("contact_number", phone).execute()
            if res.data:
                return res.data[0]
            data = {"contact_number": phone, "name": name, "is_active": True}
            return self.client.table("users").insert(data).execute().data[0]
        
        def from_memory():
            if phone not in self._users:
                self._users[phone] = {"id": phone, "contact_number": phone, "name": name, "is_active": True}
            return self._users[phone]
        
        return self._db(from_db, from_memory)
    
    def get_user_by_phone(self, phone: str) -> dict | None:
        def from_db():
            res = self.client.table("users").select("*").eq("contact_number", phone).execute()
            return res.data[0] if res.data else None
        return self._db(from_db, lambda: self._users.get(phone))
    
    def update_user(self, phone: str, **kwargs) -> dict:
        kwargs["updated_at"] = datetime.now().isoformat()
        def from_db():
            res = self.client.table("users").update(kwargs).eq("contact_number", phone).execute()
            return res.data[0] if res.data else {}
        def from_memory():
            if phone in self._users:
                self._users[phone].update(kwargs)
            return self._users.get(phone, {})
        return self._db(from_db, from_memory)
    
    def list_users(self, skip: int = 0, limit: int = 50) -> list:
        def from_db():
            return self.client.table("users").select("*").range(skip, skip + limit - 1).execute().data or []
        return self._db(from_db, lambda: list(self._users.values())[skip:skip + limit])
    
    # ==================== MENTORS ====================
    
    def get_mentors(self, active_only: bool = True) -> list:
        def from_db():
            q = self.client.table("mentors").select("id, name, email, specialty, is_active")
            if active_only:
                q = q.eq("is_active", True)
            return q.execute().data or []
        def from_memory():
            mentors = list(self._mentors.values())
            return [m for m in mentors if m.get("is_active")] if active_only else mentors
        return self._db(from_db, from_memory)
    
    def get_mentor_by_id(self, mentor_id: str) -> dict | None:
        def from_db():
            res = self.client.table("mentors").select("*").eq("id", mentor_id).execute()
            return res.data[0] if res.data else None
        return self._db(from_db, lambda: self._mentors.get(mentor_id))
    
    def get_mentor_by_email(self, email: str) -> dict | None:
        def from_db():
            res = self.client.table("mentors").select("*").eq("email", email).execute()
            return res.data[0] if res.data else None
        def from_memory():
            return next((m for m in self._mentors.values() if m.get("email") == email), None)
        return self._db(from_db, from_memory)
    
    def create_mentor(self, name: str, email: str, password_hash: str, specialty: str = None) -> dict:
        data = {"name": name, "email": email, "password_hash": password_hash, "specialty": specialty, "is_active": True}
        def from_db():
            res = self.client.table("mentors").insert(data).execute()
            m = res.data[0] if res.data else {}
            m.pop("password_hash", None)
            return m
        def from_memory():
            mid = str(len(self._mentors) + 1)
            data["id"] = mid
            self._mentors[mid] = data
            return {k: v for k, v in data.items() if k != "password_hash"}
        return self._db(from_db, from_memory)
    
    # ==================== APPOINTMENTS ====================
    
    def is_slot_booked(self, date_str: str, time_str: str, mentor_id: str = None) -> bool:
        def from_db():
            q = self.client.table("appointments").select("id").eq("date", date_str).eq("time", time_str).in_("status", ["pending", "booked"])
            if mentor_id:
                q = q.eq("mentor_id", mentor_id)
            return bool(q.execute().data)
        def from_memory():
            return any(
                a["date"] == date_str and a["time"] == time_str and a["status"] in ("pending", "booked")
                for a in self._appointments
            )
        return self._db(from_db, from_memory)
    
    def is_mentor_available(self, mentor_id: str, date_str: str, time_str: str) -> bool:
        """Check if mentor has availability set for the given date and time."""
        def from_db():
            # Check if mentor has availability entry for this date
            avail = self.client.table("mentor_availability").select("*").eq("mentor_id", mentor_id).eq("date", date_str).eq("is_available", True).execute()
            if not avail.data:
                return False
            
            # Check if time is within any availability window
            try:
                from datetime import datetime, time as dt_time
                slot_time = datetime.strptime(time_str, "%H:%M").time()
                for a in avail.data:
                    start = datetime.strptime(a["start_time"], "%H:%M:%S").time()
                    end = datetime.strptime(a["end_time"], "%H:%M:%S").time()
                    if start <= slot_time < end:
                        return True
            except Exception as e:
                logger.debug(f"Error checking mentor availability: {e}")
            return False
        
        def from_memory():
            # In-memory: assume available if not in booked list
            return True
        
        return self._db(from_db, from_memory)
    
    def book_appointment(self, phone: str, date_str: str, time_str: str, mentor_id: str = None, notes: str = None, duration_minutes: int = 60) -> dict:
        user = self.get_or_create_user(phone)
        data = {
            "user_id": user.get("id"),
            "contact_number": phone,
            "date": date_str,
            "time": time_str,
            "duration_minutes": duration_minutes,
            "status": "booked",
            "mentor_id": mentor_id,
            "notes": notes,
        }
        def from_db():
            return self.client.table("appointments").insert(data).execute().data[0]
        def from_memory():
            data["id"] = f"apt_{len(self._appointments) + 1}"
            self._appointments.append(data)
            return data
        return self._db(from_db, from_memory)
    
    def get_user_appointments(self, phone: str, status: list | str = None) -> list:
        def from_db():
            q = self.client.table("appointments").select("*, mentors(name, specialty)").eq("contact_number", phone)
            if status:
                q = q.in_("status", [status] if isinstance(status, str) else status)
            return q.order("date").order("time").execute().data or []
        def from_memory():
            apts = [a for a in self._appointments if a["contact_number"] == phone]
            if status:
                statuses = [status] if isinstance(status, str) else status
                apts = [a for a in apts if a["status"] in statuses]
            return sorted(apts, key=lambda x: (x["date"], x["time"]))
        return self._db(from_db, from_memory)
    
    def cancel_appointment(self, phone: str, date_str: str, time_str: str) -> bool:
        def from_db():
            res = self.client.table("appointments").update({"status": "cancelled"}).eq("contact_number", phone).eq("date", date_str).eq("time", time_str).in_("status", ["pending", "booked"]).execute()
            return bool(res.data)
        def from_memory():
            for apt in self._appointments:
                if apt["contact_number"] == phone and apt["date"] == date_str and apt["time"] == time_str and apt["status"] in ("pending", "booked"):
                    apt["status"] = "cancelled"
                    return True
            return False
        return self._db(from_db, from_memory)
    
    def cancel_appointment_by_id(self, appointment_id: str) -> bool:
        """Cancel appointment by ID."""
        def from_db():
            res = self.client.table("appointments").update({"status": "cancelled"}).eq("id", appointment_id).in_("status", ["pending", "booked"]).execute()
            return bool(res.data)
        def from_memory():
            for apt in self._appointments:
                if apt.get("id") == appointment_id and apt["status"] in ("pending", "booked"):
                    apt["status"] = "cancelled"
                    return True
            return False
        return self._db(from_db, from_memory)
    
    def modify_appointment(self, phone: str, old_date: str, old_time: str, new_date: str, new_time: str, mentor_id: str = None) -> dict | None:
        """Modify appointment date/time. If mentor_id provided, validates availability. Preserves mentor_id if not provided."""
        # If mentor_id provided, check availability
        if mentor_id:
            if not self.is_mentor_available(mentor_id, new_date, new_time):
                return None
            if self.is_slot_booked(new_date, new_time, mentor_id):
                return None
        else:
            # Check globally if no mentor_id
            if self.is_slot_booked(new_date, new_time):
                return None
        
        def from_db():
            # First get the appointment to preserve mentor_id
            old_apt = self.client.table("appointments").select("*").eq("contact_number", phone).eq("date", old_date).eq("time", old_time).in_("status", ["pending", "booked"]).execute()
            if not old_apt.data:
                return None
            
            existing_mentor_id = old_apt.data[0].get("mentor_id")
            # Use provided mentor_id or preserve existing one
            final_mentor_id = mentor_id if mentor_id else existing_mentor_id
            
            # Update with preserved mentor_id
            update_data = {"date": new_date, "time": new_time, "updated_at": datetime.now().isoformat()}
            if final_mentor_id:
                update_data["mentor_id"] = final_mentor_id
            
            res = self.client.table("appointments").update(update_data).eq("contact_number", phone).eq("date", old_date).eq("time", old_time).in_("status", ["pending", "booked"]).execute()
            return res.data[0] if res.data else None
        def from_memory():
            for apt in self._appointments:
                if apt["contact_number"] == phone and apt["date"] == old_date and apt["time"] == old_time and apt["status"] in ("pending", "booked"):
                    apt["date"] = new_date
                    apt["time"] = new_time
                    # Preserve or set mentor_id
                    if mentor_id:
                        apt["mentor_id"] = mentor_id
                    elif not apt.get("mentor_id"):
                        # Keep existing mentor_id
                        pass
                    return apt
            return None
        return self._db(from_db, from_memory)
    
    def get_mentor_appointments(self, mentor_id: str, status: str = None, start_date: str = None, end_date: str = None) -> list:
        def from_db():
            q = self.client.table("appointments").select("*, users(name, contact_number)").eq("mentor_id", mentor_id)
            if status:
                q = q.eq("status", status)
            if start_date:
                q = q.gte("date", start_date)
            if end_date:
                q = q.lte("date", end_date)
            return q.order("date").order("time").execute().data or []
        def from_memory():
            apts = [a for a in self._appointments if a.get("mentor_id") == mentor_id]
            if status:
                apts = [a for a in apts if a["status"] == status]
            if start_date:
                apts = [a for a in apts if a["date"] >= start_date]
            if end_date:
                apts = [a for a in apts if a["date"] <= end_date]
            return apts
        return self._db(from_db, from_memory)
    
    def list_all_appointments(self, status: str = None, mentor_id: str = None) -> list:
        def from_db():
            q = self.client.table("appointments").select("*, users(name), mentors(name)")
            if status:
                q = q.eq("status", status)
            if mentor_id:
                q = q.eq("mentor_id", mentor_id)
            return q.order("date", desc=True).execute().data or []
        def from_memory():
            apts = self._appointments.copy()
            if status:
                apts = [a for a in apts if a["status"] == status]
            if mentor_id:
                apts = [a for a in apts if a.get("mentor_id") == mentor_id]
            return apts
        return self._db(from_db, from_memory)
    
    # ==================== SESSIONS ====================
    
    def create_session(self, room_name: str, contact_number: str = None) -> dict:
        data = {"room_name": room_name, "contact_number": contact_number, "started_at": datetime.now().isoformat(), "status": "active"}
        def from_db():
            return self.client.table("sessions").insert(data).execute().data[0]
        def from_memory():
            sid = f"session_{len(self._sessions) + 1}"
            data["id"] = sid
            self._sessions[sid] = data
            return data
        return self._db(from_db, from_memory)
    
    def get_session(self, session_id: str) -> dict | None:
        def from_db():
            res = self.client.table("sessions").select("*").eq("id", session_id).execute()
            return res.data[0] if res.data else None
        return self._db(from_db, lambda: self._sessions.get(session_id))
    
    def update_session(self, session_id: str, **kwargs) -> None:
        def from_db():
            self.client.table("sessions").update(kwargs).eq("id", session_id).execute()
        def from_memory():
            if session_id in self._sessions:
                self._sessions[session_id].update(kwargs)
        self._db(from_db, from_memory)
    
    def link_session_to_user(self, session_id: str, phone: str) -> None:
        user = self.get_or_create_user(phone)
        self.update_session(session_id, contact_number=phone, user_id=user.get("id"))
    
    def log_cost(self, session_id: str, service: str, units: float, unit_type: str, cost_usd: float) -> None:
        """Log cost to cost_logs table."""
        data = {
            "session_id": session_id,
            "service": service,
            "units": float(units),  # Ensure it's a float
            "unit_type": unit_type,
            "cost_usd": float(cost_usd),  # Ensure it's a float
        }
        def from_db():
            try:
                result = self.client.table("cost_logs").insert(data).execute()
                logger.info(f"Logged cost: {service} = ${cost_usd:.6f} ({units} {unit_type})")
            except Exception as e:
                logger.error(f"Could not log cost: {e}, data: {data}")
        def from_memory():
            pass  # In-memory doesn't track costs
        self._db(from_db, from_memory)
    
    def cleanup_abandoned_sessions(self, timeout_minutes: int = 30) -> int:
        """Mark sessions as abandoned if they've been active for more than timeout_minutes."""
        cutoff_time = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()
        def from_db():
            try:
                res = self.client.table("sessions").update({"status": "abandoned"}).eq("status", "active").lt("started_at", cutoff_time).execute()
                return len(res.data) if res.data else 0
            except Exception as e:
                logger.error(f"Failed to cleanup sessions: {e}")
                return 0
        def from_memory():
            count = 0
            for sid, session in self._sessions.items():
                if session.get("status") == "active":
                    started = session.get("started_at")
                    if started:
                        try:
                            started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                            if (datetime.now() - started_dt.replace(tzinfo=None)).total_seconds() > timeout_minutes * 60:
                                session["status"] = "abandoned"
                                count += 1
                        except:
                            pass
            return count
        return self._db(from_db, from_memory)
    
    def end_session(self, session_id: str, contact_number: str = None, summary: str = None, cost_breakdown: dict = None) -> None:
        update = {"ended_at": datetime.now().isoformat(), "status": "completed"}
        if contact_number:
            update["contact_number"] = contact_number
        if summary:
            update["summary"] = summary
        if cost_breakdown:
            update["cost_breakdown"] = cost_breakdown
            
            # Log individual costs to cost_logs (always log, even if 0)
            breakdown = cost_breakdown.get("breakdown", {})
            
            # STT
            stt_minutes = breakdown.get("stt_minutes", 0)
            self.log_cost(
                session_id, "deepgram_stt",
                stt_minutes,
                "minutes",
                cost_breakdown.get("stt", 0)
            )
            
            # TTS
            tts_characters = breakdown.get("tts_characters", 0)
            self.log_cost(
                session_id, "cartesia_tts",
                tts_characters,
                "characters",
                cost_breakdown.get("tts", 0)
            )
            
            # LLM
            llm_total_tokens = breakdown.get("llm_total_tokens", 0)
            self.log_cost(
                session_id, "openai_llm",
                llm_total_tokens,
                "tokens",
                cost_breakdown.get("llm", 0)
            )
        
        session = self.get_session(session_id)
        if session and session.get("started_at"):
            try:
                started = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
                update["duration_seconds"] = int((datetime.now() - started).total_seconds())
            except:
                pass
        
        self.update_session(session_id, **update)
    
    def add_message(self, session_id: str, role: str, content: str, tool_name: str = None, tool_args: dict = None, tool_result: dict = None) -> dict:
        data = {"session_id": session_id, "role": role, "content": content, "tool_name": tool_name, "tool_args": tool_args, "tool_result": tool_result, "timestamp": datetime.now().isoformat()}
        def from_db():
            return self.client.table("session_messages").insert(data).execute().data[0]
        def from_memory():
            data["id"] = f"msg_{len(self._messages) + 1}"
            self._messages.append(data)
            return data
        return self._db(from_db, from_memory)
    
    def get_session_messages(self, session_id: str) -> list:
        def from_db():
            return self.client.table("session_messages").select("*").eq("session_id", session_id).order("timestamp").execute().data or []
        return self._db(from_db, lambda: [m for m in self._messages if m["session_id"] == session_id])
    
    def get_user_sessions(self, phone: str, limit: int = 50) -> list:
        def from_db():
            return self.client.table("sessions").select("*").eq("contact_number", phone).order("started_at", desc=True).limit(limit).execute().data or []
        def from_memory():
            sessions = [s for s in self._sessions.values() if s.get("contact_number") == phone]
            return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)[:limit]
        return self._db(from_db, from_memory)
    
    def list_all_sessions(self, status: str = None, skip: int = 0, limit: int = 50) -> list:
        def from_db():
            q = self.client.table("sessions").select("*, users(name)")
            if status:
                q = q.eq("status", status)
            return q.order("started_at", desc=True).range(skip, skip + limit - 1).execute().data or []
        def from_memory():
            sessions = list(self._sessions.values())
            if status:
                sessions = [s for s in sessions if s.get("status") == status]
            return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)[skip:skip + limit]
        return self._db(from_db, from_memory)
    
    # ==================== CONTEXT ====================
    
    def get_user_context(self, phone: str) -> dict:
        """Get comprehensive context for a user."""
        user = self.get_or_create_user(phone)
        booked = self.get_user_appointments(phone, status=["booked"])
        pending = self.get_user_appointments(phone, status=["pending"])
        sessions = self.get_user_sessions(phone, limit=5)
        last = sessions[0] if sessions else None
        
        return {
            "user": user,
            "is_returning": len(sessions) > 0,
            "total_sessions": len(sessions),
            "appointments": {"booked": booked, "pending": pending},
            "last_session": {"date": last.get("started_at") if last else None, "summary": last.get("summary") if last else None},
        }
    
    # ==================== ADMIN ====================
    
    def get_admin_by_email(self, email: str) -> dict | None:
        def from_db():
            res = self.client.table("admins").select("*").eq("email", email).execute()
            return res.data[0] if res.data else None
        def from_memory():
            # Default admin for testing
            if email == "admin@superbryn.com":
                return {"id": "1", "email": email, "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.qVYHJqI/4p4J1C", "role": "admin"}
            return None
        return self._db(from_db, from_memory)
    
    def get_admin_stats(self) -> dict:
        """Get admin dashboard statistics."""
        return {
            "total_users": len(self._users) if not self._enabled else len(self.list_users()),
            "total_mentors": len(self.get_mentors()),
            "total_sessions": len(self._sessions) if not self._enabled else len(self.list_all_sessions()),
            "total_appointments": len(self._appointments) if not self._enabled else len(self.list_all_appointments()),
        }
    
    # ==================== MENTOR AVAILABILITY ====================
    
    def get_mentor_availability(self, mentor_id: str, start_date: str = None, end_date: str = None) -> list:
        def from_db():
            q = self.client.table("mentor_availability").select("*").eq("mentor_id", mentor_id)
            if start_date:
                q = q.gte("date", start_date)
            if end_date:
                q = q.lte("date", end_date)
            return q.order("date").execute().data or []
        def from_memory():
            avail = [a for a in self._availability if a.get("mentor_id") == mentor_id]
            if start_date:
                avail = [a for a in avail if a.get("date") >= start_date]
            if end_date:
                avail = [a for a in avail if a.get("date") <= end_date]
            return avail
        return self._db(from_db, from_memory)
    
    def add_mentor_availability(self, mentor_id: str, date_str: str, start_time: str, end_time: str, slot_duration: int = 60) -> dict:
        data = {"mentor_id": mentor_id, "date": date_str, "start_time": start_time, "end_time": end_time, "slot_duration_minutes": slot_duration, "is_available": True}
        def from_db():
            return self.client.table("mentor_availability").insert(data).execute().data[0]
        def from_memory():
            data["id"] = f"avail_{len(self._availability) + 1}"
            self._availability.append(data)
            return data
        return self._db(from_db, from_memory)
    
    def remove_mentor_availability(self, availability_id: str) -> bool:
        def from_db():
            res = self.client.table("mentor_availability").delete().eq("id", availability_id).execute()
            return bool(res.data)
        def from_memory():
            self._availability = [a for a in self._availability if a.get("id") != availability_id]
            return True
        return self._db(from_db, from_memory)
    
    def get_available_slots_for_mentor(self, mentor_id: str, date_str: str) -> list:
        """Get available time slots for a mentor on a date."""
        avails = self.get_mentor_availability(mentor_id, start_date=date_str, end_date=date_str)
        if not avails:
            return []
        
        avail = avails[0]
        start = datetime.strptime(avail["start_time"], "%H:%M")
        end = datetime.strptime(avail["end_time"], "%H:%M")
        duration = avail.get("slot_duration_minutes", 60)
        
        slots = []
        current = start
        while current < end:
            time_str = current.strftime("%H:%M")
            is_booked = self.is_slot_booked(date_str, time_str, mentor_id)
            slots.append({"time": time_str, "is_booked": is_booked, "available": not is_booked})
            current += timedelta(minutes=duration)
        return slots
    
    def update_mentor(self, mentor_id: str, **kwargs) -> dict:
        kwargs["updated_at"] = datetime.now().isoformat()
        def from_db():
            res = self.client.table("mentors").update(kwargs).eq("id", mentor_id).execute()
            m = res.data[0] if res.data else {}
            m.pop("password_hash", None)
            return m
        def from_memory():
            if mentor_id in self._mentors:
                self._mentors[mentor_id].update(kwargs)
                return {k: v for k, v in self._mentors[mentor_id].items() if k != "password_hash"}
            return {}
        return self._db(from_db, from_memory)
    
    def delete_mentor(self, mentor_id: str) -> bool:
        def from_db():
            return bool(self.client.table("mentors").delete().eq("id", mentor_id).execute().data)
        def from_memory():
            if mentor_id in self._mentors:
                del self._mentors[mentor_id]
                return True
            return False
        return self._db(from_db, from_memory)
    
    def delete_user(self, phone: str) -> bool:
        def from_db():
            return bool(self.client.table("users").delete().eq("contact_number", phone).execute().data)
        def from_memory():
            if phone in self._users:
                del self._users[phone]
                return True
            return False
        return self._db(from_db, from_memory)
    
    def get_appointment_by_id(self, appointment_id: str) -> dict | None:
        def from_db():
            res = self.client.table("appointments").select("*, users(name), mentors(name)").eq("id", appointment_id).execute()
            return res.data[0] if res.data else None
        def from_memory():
            return next((a for a in self._appointments if a.get("id") == appointment_id), None)
        return self._db(from_db, from_memory)
    
    def update_appointment(self, appointment_id: str, **kwargs) -> dict:
        kwargs["updated_at"] = datetime.now().isoformat()
        def from_db():
            res = self.client.table("appointments").update(kwargs).eq("id", appointment_id).execute()
            return res.data[0] if res.data else {}
        def from_memory():
            for apt in self._appointments:
                if apt.get("id") == appointment_id:
                    apt.update(kwargs)
                    return apt
            return {}
        return self._db(from_db, from_memory)
    
    def get_mentor_calendar(self, mentor_id: str, year: int, month: int) -> dict:
        """Get calendar view for a mentor."""
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month + 1:02d}-01" if month < 12 else f"{year + 1}-01-01"
        
        appointments = self.get_mentor_appointments(mentor_id, start_date=start_date, end_date=end_date)
        availability = self.get_mentor_availability(mentor_id, start_date=start_date, end_date=end_date)
        
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
        
        return {"year": year, "month": month, "days": calendar}
    
    def get_admin_by_id(self, admin_id: str) -> dict | None:
        def from_db():
            res = self.client.table("admins").select("id, name, email, role, is_active").eq("id", admin_id).execute()
            return res.data[0] if res.data else None
        def from_memory():
            return {"id": "1", "name": "Admin", "email": "admin@superbryn.com", "role": "admin"}
        return self._db(from_db, from_memory)
    
    def update_admin_login(self, admin_id: str) -> None:
        def from_db():
            self.client.table("admins").update({"last_login": datetime.now().isoformat()}).eq("id", admin_id).execute()
        def from_memory():
            pass
        self._db(from_db, from_memory)
    
    def get_cost_report(self, start_date: str = None, end_date: str = None, group_by: str = "day") -> list:
        return []
    
    def get_session_costs(self, skip: int = 0, limit: int = 50) -> list:
        def from_db():
            return self.client.table("sessions").select("id, room_name, contact_number, started_at, ended_at, duration_seconds, summary, cost_breakdown").order("started_at", desc=True).range(skip, skip + limit - 1).execute().data or []
        def from_memory():
            sessions = list(self._sessions.values())
            return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)[skip:skip + limit]
        return self._db(from_db, from_memory)
