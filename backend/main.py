"""
Voice Agent with Beyond Presence Avatar and Full Session Tracking

Features:
- Beyond Presence (BEY) avatar for visual representation
- All 7 required tools with proper mentor assignment
- Full conversation history tracking in Supabase
- Accurate cost tracking (LLM tokens, STT, TTS)
- Returning user context - recalls previous conversations
- Real-time data channel to frontend (tool calls, transcripts)
- Session summary (cost only for admin)

Run: python backend/main.py start
"""
import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Annotated, Any
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(Path(__file__).parent / ".env")
    load_dotenv()

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.agents import metrics
from livekit.agents.metrics import UsageCollector
from livekit.plugins import cartesia, deepgram, openai, silero, bey

from db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")

BEY_AVATAR_ID = os.getenv("BEY_AVATAR_ID", "1c7a7291-ee28-4800-8f34-acfbfc2d07c0")

# Cost estimates per provider
COST_PER_UNIT = {
    "deepgram_stt": 0.0043,       # per minute
    "cartesia_tts": 0.0015,       # per 100 characters
    "openai_gpt4o_mini": 0.00015, # per 1K input tokens
    "openai_gpt4o_mini_output": 0.0006,  # per 1K output tokens
}

BASE_INSTRUCTIONS = """You are a friendly appointment booking assistant for SuperBryn.

WORKFLOW:
1. Greet the user warmly
2. Ask for their phone number to identify them (use identify_user tool)
3. Help them with their request:
   - Book new appointments: FIRST show available mentors (use list_mentors), THEN ask which mentor by NAME, THEN show slots for that mentor (fetch_slots requires mentor_id - match mentor name to get ID), THEN book
   - View their existing appointments (retrieve_appointments) - appointments will include IDs for reference
   - Modify appointment date/time (modify_appointment) - use appointment_id if available for precision
   - Cancel appointments (cancel_appointment) - use appointment_id if available for precision
4. When done, use end_conversation to summarize and end the call

GUIDELINES:
- Be conversational and natural - this is voice, keep responses concise
- ALWAYS ask the user which mentor they want by NAME before booking - NEVER auto-assign
- When listing mentors, only say their names and specialties - do NOT mention IDs
- After user chooses a mentor by name, match the name to get the mentor_id internally for fetch_slots and book_appointment
- Show available mentors first, then ask which mentor by name, then show available slots for that mentor
- Always confirm details before booking (date, time, mentor name)
- When showing appointments, mention the appointment IDs so users can reference them
- For modify/cancel, prefer using appointment_id from retrieve_appointments for accuracy
- Accept time in various formats (9 AM, 2:30 PM, 14:30, etc.) - normalize automatically
- Never allow booking or modifying to past dates/times
- If a slot is taken, suggest alternatives
- Extract dates, times, and contact info accurately
- When user says goodbye or is done, call end_conversation
- For returning users, acknowledge their history and existing appointments
- NEVER auto-assign a mentor - always ask the user to choose by name
"""


class VoiceAgent(Agent):
    """Appointment booking voice agent with full tracking and context recall."""
    
    def __init__(self, room: rtc.Room, db: Database, session_id: str, llm_session: AgentSession):
        super().__init__(instructions=BASE_INSTRUCTIONS)
        self.room = room
        self.db = db
        self.session_id = session_id
        self.llm_session = llm_session
        self.user_phone: str | None = None
        self.user_name: str | None = None
        self.user_context: dict | None = None
        
        # Use LiveKit's UsageCollector for accurate cost tracking
        self.usage_collector = UsageCollector()
    
    def _normalize_time(self, time_str: str) -> str:
        """Normalize time string to HH:MM format."""
        # Remove spaces and convert to uppercase
        time_str = time_str.strip().upper()
        
        # Handle formats like "9 AM", "9:00 AM", "9pm", etc.
        if "AM" in time_str or "PM" in time_str:
            # Parse 12-hour format
            time_part = time_str.replace("AM", "").replace("PM", "").strip()
            is_pm = "PM" in time_str
            
            if ":" in time_part:
                hour, minute = time_part.split(":")
                hour = int(hour)
                minute = int(minute)
            else:
                hour = int(time_part)
                minute = 0
            
            if is_pm and hour != 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        
        # Handle 24-hour format
        if ":" in time_str:
            parts = time_str.split(":")
            hour = parts[0].zfill(2)
            minute = parts[1][:2].zfill(2) if len(parts) > 1 else "00"
            return f"{hour}:{minute}"
        
        # Single number (assume hour)
        return f"{int(time_str):02d}:00"
    
    def _validate_date_time(self, date_str: str, time_str: str) -> tuple[bool, str]:
        """Validate that date and time are not in the past."""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            datetime_obj = datetime.combine(date_obj, time_obj)
            
            if datetime_obj < datetime.now():
                return False, f"The date and time {date_str} {time_str} is in the past. Please choose a future time."
            return True, ""
        except ValueError as e:
            return False, f"Invalid date or time format: {e}"
    
    async def send_to_frontend(self, event_type: str, data: dict):
        """Send data to frontend via LiveKit data channel."""
        try:
            payload = json.dumps({
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                **data
            }).encode()
            await self.room.local_participant.publish_data(payload, reliable=True, topic="agent_events")
            logger.debug(f"Sent to frontend: {event_type}")
        except Exception as e:
            logger.error(f"Failed to send to frontend: {e}")
    
    def calculate_cost(self) -> dict:
        """Calculate cost using LiveKit's actual usage metrics."""
        summary = self.usage_collector.get_summary()
        
        # Get actual metrics from LiveKit
        stt_audio_seconds = getattr(summary.stt, 'audio_duration', 0) if hasattr(summary, 'stt') else 0
        tts_characters = getattr(summary.tts, 'characters_count', 0) if hasattr(summary, 'tts') else 0
        tts_audio_seconds = getattr(summary.tts, 'audio_duration', 0) if hasattr(summary, 'tts') else 0
        llm_input_tokens = getattr(summary.llm, 'prompt_tokens', 0) if hasattr(summary, 'llm') else 0
        llm_output_tokens = getattr(summary.llm, 'completion_tokens', 0) if hasattr(summary, 'llm') else 0
        
        # Calculate costs using provider pricing
        stt_minutes = stt_audio_seconds / 60.0
        stt_cost = stt_minutes * COST_PER_UNIT["deepgram_stt"]
        
        # TTS: use characters (Cartesia pricing is per 100 characters)
        tts_cost = (tts_characters / 100) * COST_PER_UNIT["cartesia_tts"]
        
        # LLM: separate input/output pricing
        llm_input_cost = (llm_input_tokens / 1000) * COST_PER_UNIT["openai_gpt4o_mini"]
        llm_output_cost = (llm_output_tokens / 1000) * COST_PER_UNIT["openai_gpt4o_mini_output"]
        llm_total_cost = llm_input_cost + llm_output_cost
        
        return {
            "stt": round(stt_cost, 6),
            "tts": round(tts_cost, 6),
            "llm": round(llm_total_cost, 6),
            "total": round(stt_cost + tts_cost + llm_total_cost, 6),
            "breakdown": {
                "stt_audio_seconds": round(stt_audio_seconds, 2),
                "stt_minutes": round(stt_minutes, 2),
                "tts_characters": int(tts_characters),
                "tts_audio_seconds": round(tts_audio_seconds, 2),
                "llm_input_tokens": int(llm_input_tokens),
                "llm_output_tokens": int(llm_output_tokens),
                "llm_total_tokens": int(llm_input_tokens + llm_output_tokens),
            }
        }
    
    
    def _load_user_context(self, phone: str) -> dict:
        self.user_context = self.db.get_user_context(phone)
        return self.user_context
    
    def _build_context_aware_response(self, context: dict) -> str:
        user = context.get("user", {})
        name = user.get("name", "there")
        is_returning = context.get("is_returning", False)
        booked = context.get("appointments", {}).get("booked", [])
        pending = context.get("appointments", {}).get("pending", [])
        last_summary = context.get("last_session", {}).get("summary")
        
        if not is_returning:
            return f"Hello {name}! I've registered your phone number. How can I help you today? Would you like to book an appointment?"
        
        parts = [f"Welcome back, {name}!"]
        if booked:
            if len(booked) == 1:
                apt = booked[0]
                mentor_name = apt.get("mentors", {}).get("name", "a consultant") if isinstance(apt.get("mentors"), dict) else "a consultant"
                parts.append(f"You have an appointment on {apt['date']} at {apt['time']} with {mentor_name}.")
            else:
                parts.append(f"You have {len(booked)} upcoming appointments.")
        if pending:
            parts.append(f"You also have {len(pending)} pending appointment(s) to confirm.")
        if last_summary and not booked and not pending:
            parts.append(f"Last time we spoke, {last_summary.lower()}")
        parts.append("How can I help you today?")
        return " ".join(parts)
    
    # ==================== TOOLS ====================
    
    @function_tool()
    async def list_mentors(self, context: RunContext) -> str:
        """List all available mentors with their specialties and IDs."""
        mentors = self.db.get_mentors(active_only=True)
        if not mentors:
            return "Sorry, no mentors are available at the moment."
        
        # For voice response: only names and specialties (no IDs)
        mentor_list_voice = []
        for i, mentor in enumerate(mentors, 1):
            name = mentor.get("name", "Unknown")
            specialty = mentor.get("specialty", "General")
            # Format: "1. Dr. Sarah Smith - General Consultation"
            mentor_list_voice.append(f"{i}. {name} - {specialty}")
        
        self.db.add_message(self.session_id, "tool", f"Listed {len(mentors)} mentors", 
                           tool_name="list_mentors", tool_args={}, 
                           tool_result={"count": len(mentors), "mentors": mentors})
        
        await self.send_to_frontend("tool_call", {
            "tool": "list_mentors",
            "args": {},
            "result": {"mentors": mentors}
        })
        
        mentor_text = "\n".join(mentor_list_voice)
        return f"Here are our available mentors:\n{mentor_text}\n\nWhich mentor would you like to book with? Please tell me the mentor's name."
    
    @function_tool()
    async def identify_user(
        self,
        context: RunContext,
        phone_number: Annotated[str, "User's phone number (10 digits or with country code)"],
        name: Annotated[str | None, "User's name if provided"] = None,
    ) -> str:
        """Identify and register a user by their phone number."""
        phone = "".join(filter(str.isdigit, phone_number))
        if len(phone) == 10:
            phone = f"+1{phone}"
        elif not phone.startswith("+"):
            phone = f"+{phone}"
        
        user = self.db.get_or_create_user(phone, name or "User")
        self.user_phone = phone
        self.user_name = user.get("name", "User")
        
        if name and name != user.get("name"):
            self.db.update_user(phone, name=name)
            self.user_name = name
        
        self.db.link_session_to_user(self.session_id, phone)
        user_context = self._load_user_context(phone)
        
        self.db.add_message(
            self.session_id, "tool", f"Identified user: {phone}",
            tool_name="identify_user",
            tool_args={"phone_number": phone_number, "name": name},
            tool_result={"phone": phone, "name": self.user_name, "is_returning": user_context.get("is_returning", False)}
        )
        
        await self.send_to_frontend("tool_call", {
            "tool": "identify_user",
            "args": {"phone": phone},
            "result": {"success": True, "name": self.user_name, "is_returning": user_context.get("is_returning", False)}
        })
        
        await self.send_to_frontend("context_loaded", {
            "user": {"phone": phone, "name": self.user_name},
            "is_returning": user_context.get("is_returning", False),
            "total_sessions": user_context.get("total_sessions", 0),
            "appointments": user_context.get("appointments", {}),
        })
        
        logger.info(f"User identified: {phone}, returning: {user_context.get('is_returning')}")
        return self._build_context_aware_response(user_context)
    
    @function_tool()
    async def fetch_slots(
        self,
        context: RunContext,
        mentor_id: Annotated[str | None, "Mentor ID - get from list_mentors result"] = None,
        mentor_name: Annotated[str | None, "Mentor name - alternative to mentor_id"] = None,
        date: Annotated[str | None, "Specific date in YYYY-MM-DD format, or None for next available days"] = None,
    ) -> str:
        """Fetch available appointment slots for a specific mentor. Provide either mentor_id (from list_mentors) or mentor_name."""
        # If mentor_name provided, find the mentor_id
        if mentor_name and not mentor_id:
            mentors = self.db.get_mentors(active_only=True)
            matching_mentor = next((m for m in mentors if m.get("name", "").lower() == mentor_name.lower()), None)
            if matching_mentor:
                mentor_id = matching_mentor.get("id")
            else:
                return f"Sorry, I couldn't find a mentor named '{mentor_name}'. Please use list_mentors to see available mentors."
        
        if not mentor_id:
            return "Please select a mentor first using list_mentors tool."
        
        # Check if mentor has availability set
        mentor = self.db.get_mentor_by_id(mentor_id)
        if not mentor:
            return "Invalid mentor. Please use list_mentors to see available mentors."
        
        # Check mentor availability for the date range
        slots = []
        try:
            start_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date() + timedelta(days=1)
        except ValueError:
            start_date = datetime.now().date() + timedelta(days=1)
        
        for day_offset in range(5):
            slot_date = start_date + timedelta(days=day_offset)
            if slot_date.weekday() >= 5:
                continue
            date_str = slot_date.strftime("%Y-%m-%d")
            day_name = slot_date.strftime("%A")
            
            # Check mentor availability for this date
            availability = self.db.get_mentor_availability(mentor_id, start_date=date_str, end_date=date_str)
            if not availability:
                continue  # Mentor not available on this date
            
            # Get available slots from mentor_availability
            for avail in availability:
                start_time = datetime.strptime(avail["start_time"], "%H:%M:%S").time()
                end_time = datetime.strptime(avail["end_time"], "%H:%M:%S").time()
                slot_duration = avail.get("slot_duration_minutes", 60)
                
                current_time = start_time
                while current_time < end_time:
                    time_str = current_time.strftime("%H:%M")
                    # Check if slot is not booked (is_mentor_available already checked via get_mentor_availability)
                    if not self.db.is_slot_booked(date_str, time_str, mentor_id):
                        slots.append({
                            "date": date_str,
                            "day": day_name,
                            "time": time_str,
                            "display": f"{day_name} {date_str} at {time_str}",
                            "mentor_id": mentor_id
                        })
                    
                    # Move to next slot
                    current_time = (datetime.combine(datetime.today(), current_time) + 
                                   timedelta(minutes=slot_duration)).time()
        
        self.db.add_message(self.session_id, "tool", f"Fetched {len(slots)} slots for mentor", 
                           tool_name="fetch_slots", tool_args={"mentor_id": mentor_id, "date": date}, 
                           tool_result={"slots_count": len(slots)})
        await self.send_to_frontend("tool_call", {"tool": "fetch_slots", "args": {"mentor_id": mentor_id, "date": date}, 
                                                 "result": {"slots": slots[:8]}})
        
        if not slots:
            return f"No available slots found for {mentor.get('name')}. Would you like to try a different mentor or date?"
        
        slot_list = "\n".join([s["display"] for s in slots[:5]])
        return f"Here are the available slots for {mentor.get('name')}:\n{slot_list}\n\nWhich one would you like?"
    
    @function_tool()
    async def book_appointment(
        self,
        context: RunContext,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        time: Annotated[str, "Time in HH:MM 24-hour format or 12-hour format (e.g., '9 AM', '2:30 PM')"],
        mentor_id: Annotated[str | None, "Mentor ID - get from list_mentors result"] = None,
        mentor_name: Annotated[str | None, "Mentor name - alternative to mentor_id"] = None,
        notes: Annotated[str | None, "Any notes for the appointment"] = None,
    ) -> str:
        """Book an appointment for the identified user with a specific mentor. Provide either mentor_id (from list_mentors) or mentor_name."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        # If mentor_name provided, find the mentor_id
        if mentor_name and not mentor_id:
            mentors = self.db.get_mentors(active_only=True)
            matching_mentor = next((m for m in mentors if m.get("name", "").lower() == mentor_name.lower()), None)
            if matching_mentor:
                mentor_id = matching_mentor.get("id")
            else:
                return f"Sorry, I couldn't find a mentor named '{mentor_name}'. Please use list_mentors to see available mentors."
        
        if not mentor_id:
            return "Please select a mentor first using list_mentors tool."
        
        # Normalize time format
        time = self._normalize_time(time)
        
        # Validate date/time is not in the past
        is_valid, error_msg = self._validate_date_time(date, time)
        if not is_valid:
            await self.send_to_frontend("tool_call", {"tool": "book_appointment", "args": {"date": date, "time": time}, 
                                                  "result": {"success": False, "reason": error_msg}})
            return error_msg
        
        # Verify mentor exists
        mentor = self.db.get_mentor_by_id(mentor_id)
        if not mentor:
            return "Invalid mentor. Please use list_mentors to see available mentors."
        
        # Check if mentor has availability for this date/time
        if not self.db.is_mentor_available(mentor_id, date, time):
            return f"Sorry, {mentor.get('name')} is not available on {date} at {time}. Would you like to see other available slots?"
        
        # Check if slot is booked
        if self.db.is_slot_booked(date, time, mentor_id):
            await self.send_to_frontend("tool_call", {"tool": "book_appointment", "args": {"date": date, "time": time}, 
                                                  "result": {"success": False, "reason": "Slot already booked"}})
            return f"Sorry, {date} at {time} is already booked with {mentor.get('name')}. Would you like a different time?"
        
        # Book appointment
        appointment = self.db.book_appointment(self.user_phone, date, time, mentor_id=mentor_id, notes=notes, duration_minutes=60)
        appointment_id = appointment.get("id")
        
        self.db.add_message(
            self.session_id, "tool", f"Booked: {date} {time} with {mentor.get('name')}",
            tool_name="book_appointment",
            tool_args={"date": date, "time": time, "mentor_id": mentor_id, "notes": notes},
            tool_result={"success": True, "appointment_id": appointment_id, "mentor_name": mentor.get("name"), "mentor_id": mentor_id}
        )
        
        await self.send_to_frontend("tool_call", {
            "tool": "book_appointment",
            "args": {"date": date, "time": time, "mentor_id": mentor_id},
            "result": {"success": True, "appointment": appointment, "appointment_id": appointment_id, "mentor_name": mentor.get("name")}
        })
        
        logger.info(f"Booked: {self.user_phone} on {date} at {time} with {mentor.get('name')} (appointment_id: {appointment_id}, mentor_id: {mentor_id})")
        return f"Done! Your appointment is confirmed for {date} at {time} with {mentor.get('name')}. Appointment ID: {appointment_id}. Is there anything else?"
    
    @function_tool()
    async def retrieve_appointments(self, context: RunContext) -> str:
        """Retrieve user's existing appointments with IDs for reference."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        appointments = self.db.get_user_appointments(self.user_phone, status=["pending", "booked"])
        self.db.add_message(self.session_id, "tool", f"Retrieved {len(appointments)} appointments", tool_name="retrieve_appointments", tool_args={}, tool_result={"count": len(appointments), "appointments": appointments})
        await self.send_to_frontend("tool_call", {"tool": "retrieve_appointments", "args": {}, "result": {"appointments": appointments}})
        
        if not appointments:
            return "You don't have any upcoming appointments. Would you like to book one?"
        
        apt_list = []
        for i, apt in enumerate(appointments, 1):
            appointment_id = apt.get("id", "")
            mentor_info = apt.get("mentors")
            if isinstance(mentor_info, dict):
                mentor_name = mentor_info.get("name", "a consultant")
            else:
                mentor_name = "a consultant"
            # Format: "1. 2024-01-22 at 14:00 with Dr. Sarah Smith (ID: abc-123)"
            apt_list.append(f"{i}. {apt['date']} at {apt['time']} with {mentor_name} (ID: {appointment_id})")
        
        return f"Your upcoming appointments:\n" + "\n".join(apt_list) + "\n\nWould you like to modify or cancel any? Please provide the appointment ID or date and time."
    
    @function_tool()
    async def cancel_appointment(
        self,
        context: RunContext,
        date: Annotated[str, "Date of appointment to cancel (YYYY-MM-DD)"],
        time: Annotated[str, "Time of appointment to cancel (HH:MM or 12-hour format)"],
        appointment_id: Annotated[str | None, "Appointment ID if available (from retrieve_appointments)"] = None,
    ) -> str:
        """Cancel an existing appointment. Use appointment_id if available, otherwise use date and time."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        # Normalize time
        time = self._normalize_time(time)
        
        # If appointment_id provided, use it for more precise cancellation
        if appointment_id:
            appointment = self.db.get_appointment_by_id(appointment_id)
            if not appointment:
                return f"Appointment with ID {appointment_id} not found. Would you like to see your appointments?"
            
            # Verify appointment belongs to user
            if appointment.get("contact_number") != self.user_phone:
                return "This appointment doesn't belong to you. Would you like to see your appointments?"
            
            # Cancel by ID
            success = self.db.cancel_appointment_by_id(appointment_id)
            mentor_name = "a consultant"
            if isinstance(appointment.get("mentors"), dict):
                mentor_name = appointment.get("mentors", {}).get("name", "a consultant")
            
            self.db.add_message(self.session_id, "tool", f"Cancel: {appointment_id}", 
                              tool_name="cancel_appointment", 
                              tool_args={"appointment_id": appointment_id, "date": date, "time": time}, 
                              tool_result={"success": success, "appointment_id": appointment_id, "mentor_name": mentor_name})
            await self.send_to_frontend("tool_call", {"tool": "cancel_appointment", "args": {"appointment_id": appointment_id}, "result": {"success": success, "appointment_id": appointment_id}})
            
            if success:
                return f"Your appointment on {appointment.get('date')} at {appointment.get('time')} with {mentor_name} has been cancelled. Anything else?"
            return f"Failed to cancel appointment {appointment_id}. Would you like to see your appointments?"
        
        # Fallback to date/time matching
        # First, find the appointment to get details
        appointments = self.db.get_user_appointments(self.user_phone, status=["pending", "booked"])
        matching_apt = None
        for apt in appointments:
            if apt.get("date") == date and apt.get("time") == time:
                matching_apt = apt
                break
        
        if not matching_apt:
            return f"I couldn't find an active appointment on {date} at {time}. Would you like to see your appointments?"
        
        # Cancel by date/time
        success = self.db.cancel_appointment(self.user_phone, date, time)
        mentor_name = "a consultant"
        if isinstance(matching_apt.get("mentors"), dict):
            mentor_name = matching_apt.get("mentors", {}).get("name", "a consultant")
        
        self.db.add_message(self.session_id, "tool", f"Cancel: {date} {time}", 
                          tool_name="cancel_appointment", 
                          tool_args={"date": date, "time": time}, 
                          tool_result={"success": success, "appointment_id": matching_apt.get("id"), "mentor_name": mentor_name})
        await self.send_to_frontend("tool_call", {"tool": "cancel_appointment", "args": {"date": date, "time": time}, "result": {"success": success, "appointment_id": matching_apt.get("id")}})
        
        if success:
            return f"Your appointment on {date} at {time} with {mentor_name} has been cancelled. Appointment ID: {matching_apt.get('id')}. Anything else?"
        return f"I couldn't cancel the appointment on {date} at {time}. Would you like to see your appointments?"
    
    @function_tool()
    async def modify_appointment(
        self,
        context: RunContext,
        old_date: Annotated[str, "Current appointment date (YYYY-MM-DD)"],
        old_time: Annotated[str, "Current appointment time (HH:MM or 12-hour format)"],
        new_date: Annotated[str, "New date (YYYY-MM-DD)"],
        new_time: Annotated[str, "New time (HH:MM or 12-hour format)"],
        appointment_id: Annotated[str | None, "Appointment ID if available (from retrieve_appointments)"] = None,
    ) -> str:
        """Modify an existing appointment's date and/or time. Preserves mentor assignment."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        # Normalize times
        old_time = self._normalize_time(old_time)
        new_time = self._normalize_time(new_time)
        
        # Validate new date/time is not in the past
        is_valid, error_msg = self._validate_date_time(new_date, new_time)
        if not is_valid:
            await self.send_to_frontend("tool_call", {"tool": "modify_appointment", "args": {"old_date": old_date, "new_date": new_date}, "result": {"success": False, "reason": error_msg}})
            return error_msg
        
        # Find the original appointment to get mentor_id
        original_appointment = None
        if appointment_id:
            original_appointment = self.db.get_appointment_by_id(appointment_id)
            if not original_appointment:
                return f"Appointment with ID {appointment_id} not found. Would you like to see your appointments?"
            if original_appointment.get("contact_number") != self.user_phone:
                return "This appointment doesn't belong to you. Would you like to see your appointments?"
        else:
            # Find by date/time
            appointments = self.db.get_user_appointments(self.user_phone, status=["pending", "booked"])
            for apt in appointments:
                if apt.get("date") == old_date and apt.get("time") == old_time:
                    original_appointment = apt
                    break
        
        if not original_appointment:
            return f"I couldn't find your appointment on {old_date} at {old_time}. Would you like to see your appointments?"
        
        mentor_id = original_appointment.get("mentor_id")
        if not mentor_id:
            return f"Your appointment on {old_date} at {old_time} doesn't have a mentor assigned. Please contact support."
        
        # Verify mentor still exists
        mentor = self.db.get_mentor_by_id(mentor_id)
        if not mentor:
            return f"The mentor for your appointment is no longer available. Please book a new appointment."
        
        # Check if new slot has mentor availability
        if not self.db.is_mentor_available(mentor_id, new_date, new_time):
            await self.send_to_frontend("tool_call", {"tool": "modify_appointment", "args": {"old_date": old_date, "new_date": new_date}, "result": {"success": False, "reason": "Mentor not available"}})
            return f"Sorry, {mentor.get('name')} is not available on {new_date} at {new_time}. Would you like to pick another time?"
        
        # Check if new slot is booked for this mentor
        if self.db.is_slot_booked(new_date, new_time, mentor_id):
            await self.send_to_frontend("tool_call", {"tool": "modify_appointment", "args": {"old_date": old_date, "new_date": new_date}, "result": {"success": False, "reason": "Slot already booked"}})
            return f"Sorry, {new_date} at {new_time} is already booked with {mentor.get('name')}. Would you like to pick another time?"
        
        # Modify appointment (preserving mentor_id)
        result = self.db.modify_appointment(self.user_phone, old_date, old_time, new_date, new_time, mentor_id=mentor_id)
        
        appointment_id = original_appointment.get("id")
        self.db.add_message(self.session_id, "tool", f"Modify: {old_date} {old_time} → {new_date} {new_time}", 
                          tool_name="modify_appointment", 
                          tool_args={"old_date": old_date, "old_time": old_time, "new_date": new_date, "new_time": new_time, "appointment_id": appointment_id}, 
                          tool_result={"success": bool(result), "appointment_id": appointment_id, "mentor_name": mentor.get("name")})
        await self.send_to_frontend("tool_call", {"tool": "modify_appointment", "args": {"old_date": old_date, "new_date": new_date}, "result": {"success": bool(result), "appointment_id": appointment_id}})
        
        if result:
            return f"Appointment moved from {old_date} at {old_time} to {new_date} at {new_time} with {mentor.get('name')}. Appointment ID: {appointment_id}. Anything else?"
        return f"I couldn't modify your appointment on {old_date} at {old_time}."
    
    @function_tool()
    async def end_conversation(self, context: RunContext) -> str:
        """End the conversation and generate summary. Cost breakdown is only for admin, not shown to user."""
        messages = self.db.get_session_messages(self.session_id)
        appointments = self.db.get_user_appointments(self.user_phone, status="booked") if self.user_phone else []
        
        actions_taken = [m for m in messages if m.get("role") == "tool" and m.get("tool_name")]
        summary_parts = []
        for msg in actions_taken:
            tool, result, args = msg.get("tool_name"), msg.get("tool_result") or {}, msg.get("tool_args") or {}
            if tool == "book_appointment" and result.get("success"):
                mentor_name = result.get("mentor_name", "a consultant")
                apt_id = result.get("appointment_id", "")
                summary_parts.append(f"Booked appointment for {args.get('date')} at {args.get('time')} with {mentor_name} (ID: {apt_id})")
            elif tool == "cancel_appointment" and result.get("success"):
                mentor_name = result.get("mentor_name", "a consultant")
                apt_id = result.get("appointment_id", "")
                summary_parts.append(f"Cancelled appointment for {args.get('date')} at {args.get('time', '')} with {mentor_name} (ID: {apt_id})")
            elif tool == "modify_appointment" and result.get("success"):
                mentor_name = result.get("mentor_name", "a consultant")
                apt_id = result.get("appointment_id", "")
                summary_parts.append(f"Moved appointment from {args.get('old_date')} at {args.get('old_time', '')} to {args.get('new_date')} at {args.get('new_time', '')} with {mentor_name} (ID: {apt_id})")
        
        # Calculate cost (for admin only, not shown to user)
        cost = self.calculate_cost()
        summary_text = "; ".join(summary_parts) if summary_parts else "No changes made"
        
        # User-facing summary (no cost)
        user_summary = {
            "user_phone": self.user_phone,
            "user_name": self.user_name,
            "actions": summary_parts,
            "upcoming_appointments": [{"date": apt["date"], "time": apt["time"]} for apt in appointments],
        }
        
        # Admin summary (with cost)
        admin_summary = {**user_summary, "cost_breakdown": cost}
        
        # Save session with cost (for admin)
        self.db.end_session(self.session_id, contact_number=self.user_phone, summary=summary_text, cost_breakdown=cost)
        
        # Send user-facing summary (no cost)
        await self.send_to_frontend("summary", user_summary)
        await self.send_to_frontend("tool_call", {"tool": "end_conversation", "args": {}, "result": {"summary": user_summary}})
        
        response = "Here's a summary: "
        response += ". ".join(summary_parts) + ". " if summary_parts else "We discussed your appointments. "
        if appointments:
            response += f"You have {len(appointments)} upcoming appointment{'s' if len(appointments) > 1 else ''}. "
        response += "Thank you for using SuperBryn!"
        
        logger.info(f"Session ended: {self.session_id}, cost: ${cost['total']:.4f}")
        return response


async def entrypoint(ctx: JobContext):
    """LiveKit Agent entrypoint with Beyond Presence avatar."""
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    
    logger.info(f"Connected to room: {ctx.room.name}")
    
    db = Database()
    
    # Cleanup abandoned sessions periodically (every session start)
    try:
        cleaned = db.cleanup_abandoned_sessions(timeout_minutes=30)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} abandoned sessions")
    except Exception as e:
        logger.debug(f"Session cleanup error (non-critical): {e}")
    
    session_record = db.create_session(room_name=ctx.room.name)
    session_id = session_record["id"]
    
    logger.info(f"Session created: {session_id} for room: {ctx.room.name}")
    
    # Create AgentSession with STT, LLM, TTS (but don't start it yet)
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-2", language="en-US"),
        llm=openai.LLM(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        tts=cartesia.TTS(
            model="sonic-2",
            voice=os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091"),
            language="en",
        ),
        allow_interruptions=True,
    )
    
    # Create agent
    agent = VoiceAgent(room=ctx.room, db=db, session_id=session_id, llm_session=session)
    loop = asyncio.get_running_loop()
    
    # Hook into LiveKit's metrics_collected event for accurate cost tracking
    @session.on("metrics_collected")
    def on_metrics_collected(ev: Any):
        """Collect actual usage metrics from LiveKit."""
        try:
            # The event might be the metrics object itself, or have a 'metrics' attribute
            # Try to get metrics from event, fallback to event itself
            metrics_data = getattr(ev, 'metrics', ev)
            if metrics_data:
                agent.usage_collector.collect(metrics_data)
                logger.debug(f"Metrics collected: {type(metrics_data)}")
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
    
    # Track transcripts (for display, not cost - cost comes from metrics)
    @session.on("user_speech_committed")
    def on_user_speech(ev):
        text = getattr(ev, 'text', '') or getattr(ev, 'transcript', '')
        if text:
            db.add_message(session_id, "user", text)
            loop.create_task(agent.send_to_frontend("transcript", {"role": "user", "text": text}))
    
    @session.on("agent_speech_committed")
    def on_agent_speech(ev):
        text = getattr(ev, 'text', '') or getattr(ev, 'transcript', '')
        if text:
            db.add_message(session_id, "assistant", text)
            loop.create_task(agent.send_to_frontend("transcript", {"role": "assistant", "text": text}))
    
    # Create Beyond Presence avatar session
    avatar = bey.AvatarSession(
        avatar_id=BEY_AVATAR_ID,
        avatar_participant_identity="avatar-agent",
        avatar_participant_name="SuperBryn Assistant",
    )
    
    # Start avatar FIRST and WAIT for it to be ready before starting STT/TTS
    logger.info(f"Starting Beyond Presence avatar: {BEY_AVATAR_ID}")
    logger.info("⏳ Waiting for avatar video to connect before starting STT/TTS...")
    
    # Start avatar and wait for it to be fully connected (this blocks until avatar is ready)
    await avatar.start(session, room=ctx.room)
    
    logger.info("✅ Avatar connected! Now starting STT/TTS session...")
    
    # Now start the agent session with STT/TTS (avatar is already ready)
    await session.start(agent=agent, room=ctx.room)
    
    # Send signal to frontend that avatar and STT/TTS are ready
    await agent.send_to_frontend("avatar_ready", {"status": "connected", "stt_tts_ready": True})
    
    logger.info("✅ STT/TTS session started! Avatar and voice are ready.")
    
    # Initial greeting (only after everything is ready)
    await session.say(
        "Hello! I'm your SuperBryn appointment assistant. "
        "To get started, could you please tell me your phone number?"
    )
    
    logger.info(f"Agent ready for session: {session_id}")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
