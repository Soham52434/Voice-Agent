"""
Simple database operations using Supabase.
This is the ONLY database file needed.
"""
import os
from datetime import datetime
from typing import Any
from dotenv import load_dotenv

load_dotenv()


class Database:
    """
    Supabase database wrapper.
    Falls back to in-memory storage if Supabase is not configured.
    """
    
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
            # In-memory fallback
            self._users: dict[str, dict] = {}
            self._appointments: list[dict] = []
            self._conversations: list[dict] = []
    
    # ==================== USERS ====================
    
    def get_or_create_user(self, phone: str) -> dict[str, Any]:
        """Get existing user or create new one."""
        if not self._enabled:
            if phone not in self._users:
                self._users[phone] = {"phone": phone, "name": "User", "created_at": datetime.now().isoformat()}
            return self._users[phone]
        
        # Try to find existing user
        response = self.client.table("users").select("*").eq("contact_number", phone).execute()
        
        if response.data:
            return response.data[0]
        
        # Create new user
        user_data = {
            "contact_number": phone,
            "name": "User",
            "created_at": datetime.now().isoformat(),
        }
        response = self.client.table("users").insert(user_data).execute()
        return response.data[0] if response.data else user_data
    
    # ==================== APPOINTMENTS ====================
    
    def is_slot_booked(self, date: str, time: str) -> bool:
        """Check if a slot is already booked."""
        if not self._enabled:
            return any(
                apt["date"] == date and apt["time"] == time and apt["status"] == "booked"
                for apt in self._appointments
            )
        
        response = (
            self.client.table("appointments")
            .select("id")
            .eq("date", date)
            .eq("time", time)
            .eq("status", "booked")
            .execute()
        )
        return bool(response.data)
    
    def book_appointment(self, phone: str, date: str, time: str) -> dict[str, Any]:
        """Book a new appointment."""
        apt_data = {
            "contact_number": phone,
            "date": date,
            "time": time,
            "status": "booked",
            "created_at": datetime.now().isoformat(),
        }
        
        if not self._enabled:
            self._appointments.append(apt_data)
            return apt_data
        
        response = self.client.table("appointments").insert(apt_data).execute()
        return response.data[0] if response.data else apt_data
    
    def get_user_appointments(self, phone: str) -> list[dict[str, Any]]:
        """Get all active appointments for a user."""
        if not self._enabled:
            return [
                apt for apt in self._appointments
                if apt["contact_number"] == phone and apt["status"] == "booked"
            ]
        
        response = (
            self.client.table("appointments")
            .select("*")
            .eq("contact_number", phone)
            .eq("status", "booked")
            .order("date")
            .order("time")
            .execute()
        )
        return response.data or []
    
    def cancel_appointment(self, phone: str, date: str, time: str) -> bool:
        """Cancel an appointment."""
        if not self._enabled:
            for apt in self._appointments:
                if (apt["contact_number"] == phone and 
                    apt["date"] == date and 
                    apt["time"] == time and 
                    apt["status"] == "booked"):
                    apt["status"] = "cancelled"
                    return True
            return False
        
        response = (
            self.client.table("appointments")
            .update({"status": "cancelled", "updated_at": datetime.now().isoformat()})
            .eq("contact_number", phone)
            .eq("date", date)
            .eq("time", time)
            .eq("status", "booked")
            .execute()
        )
        return bool(response.data)
    
    # ==================== CONVERSATIONS ====================
    
    def save_conversation(self, phone: str, summary: str, actions: list[dict]) -> None:
        """Save conversation summary."""
        conv_data = {
            "contact_number": phone,
            "summary": summary,
            "actions": actions,
            "created_at": datetime.now().isoformat(),
        }
        
        if not self._enabled:
            self._conversations.append(conv_data)
            print(f"📝 Conversation saved: {summary}")
            return
        
        self.client.table("conversations").insert(conv_data).execute()

