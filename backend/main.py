"""
Voice Agent with Full Session Tracking and Context Retrieval

Features:
- All 7 required tools (identify_user, fetch_slots, book_appointment, 
  retrieve_appointments, cancel_appointment, modify_appointment, end_conversation)
- Full conversation history tracking in Supabase
- Returning user context - recalls previous conversations
- Real-time data channel to frontend (tool calls, transcripts)
- Cost estimation
- Session summary

Run: python backend/main.py dev
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Annotated
from dotenv import load_dotenv

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
from livekit.plugins import cartesia, deepgram, openai, silero

from db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")


# Cost estimates per provider (approximate)
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
   - Book new appointments (show available slots first with fetch_slots)
   - View their existing appointments (retrieve_appointments)
   - Modify appointment date/time (modify_appointment)
   - Cancel appointments (cancel_appointment)
4. When done, use end_conversation to summarize and end the call

GUIDELINES:
- Be conversational and natural - this is voice, keep responses concise
- Always confirm details before booking
- If a slot is taken, suggest alternatives
- Extract dates, times, and contact info accurately
- When user says goodbye or is done, call end_conversation
- For returning users, acknowledge their history and existing appointments

AVAILABLE MENTORS:
- Dr. Sarah Smith (General Consultation)
- Dr. John Doe (Technical Review)
"""


class VoiceAgent(Agent):
    """
    Appointment booking voice agent with full tracking and context recall.
    
    Sends real-time events to frontend via LiveKit data channel:
    - tool_call: When a tool is invoked
    - transcript: User/assistant speech
    - summary: End of call summary
    - context_loaded: When returning user context is loaded
    """
    
    def __init__(self, room: rtc.Room, db: Database, session_id: str):
        super().__init__(instructions=BASE_INSTRUCTIONS)
        self.room = room
        self.db = db
        self.session_id = session_id
        self.user_phone: str | None = None
        self.user_name: str | None = None
        self.user_context: dict | None = None  # Stores loaded user context
        
        # Cost tracking
        self.cost_tracker = {
            "stt_minutes": 0.0,
            "tts_characters": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
        }
    
    async def send_to_frontend(self, event_type: str, data: dict):
        """Send data to frontend via LiveKit data channel."""
        try:
            payload = json.dumps({
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                **data
            }).encode()
            
            await self.room.local_participant.publish_data(
                payload,
                reliable=True,
                topic="agent_events"
            )
            logger.debug(f"Sent to frontend: {event_type}")
        except Exception as e:
            logger.error(f"Failed to send to frontend: {e}")
    
    def calculate_cost(self) -> dict:
        """Calculate total cost breakdown."""
        stt_cost = self.cost_tracker["stt_minutes"] * COST_PER_UNIT["deepgram_stt"]
        tts_cost = (self.cost_tracker["tts_characters"] / 100) * COST_PER_UNIT["cartesia_tts"]
        llm_input_cost = (self.cost_tracker["llm_input_tokens"] / 1000) * COST_PER_UNIT["openai_gpt4o_mini"]
        llm_output_cost = (self.cost_tracker["llm_output_tokens"] / 1000) * COST_PER_UNIT["openai_gpt4o_mini_output"]
        
        return {
            "stt": round(stt_cost, 4),
            "tts": round(tts_cost, 4),
            "llm": round(llm_input_cost + llm_output_cost, 4),
            "total": round(stt_cost + tts_cost + llm_input_cost + llm_output_cost, 4),
            "breakdown": {
                "stt_minutes": round(self.cost_tracker["stt_minutes"], 2),
                "tts_characters": self.cost_tracker["tts_characters"],
                "llm_tokens": self.cost_tracker["llm_input_tokens"] + self.cost_tracker["llm_output_tokens"],
            }
        }
    
    def _load_user_context(self, phone: str) -> dict:
        """Load and cache user context from database."""
        self.user_context = self.db.get_user_context(phone)
        return self.user_context
    
    def _build_context_aware_response(self, context: dict) -> str:
        """Build a personalized response based on user context."""
        user = context.get("user", {})
        name = user.get("name", "there")
        is_returning = context.get("is_returning", False)
        
        booked = context.get("appointments", {}).get("booked", [])
        pending = context.get("appointments", {}).get("pending", [])
        last_summary = context.get("last_session", {}).get("summary")
        
        if not is_returning:
            return f"Hello {name}! I've registered your phone number. How can I help you today? Would you like to book an appointment?"
        
        # Returning user - personalized greeting
        parts = [f"Welcome back, {name}!"]
        
        if booked:
            if len(booked) == 1:
                apt = booked[0]
                parts.append(f"You have an appointment on {apt['date']} at {apt['time']}.")
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
    async def identify_user(
        self,
        context: RunContext,
        phone_number: Annotated[str, "User's phone number (10 digits or with country code)"],
        name: Annotated[str | None, "User's name if provided"] = None,
    ) -> str:
        """Identify and register a user by their phone number. This loads their conversation history and appointments."""
        # Normalize phone number
        phone = "".join(filter(str.isdigit, phone_number))
        if len(phone) == 10:
            phone = f"+1{phone}"
        elif not phone.startswith("+"):
            phone = f"+{phone}"
        
        # Get or create user
        user = self.db.get_or_create_user(phone, name or "User")
        self.user_phone = phone
        self.user_name = user.get("name", "User")
        
        # Update name if provided
        if name and name != user.get("name"):
            self.db.update_user(phone, name=name)
            self.user_name = name
        
        # Link session to user
        self.db.link_session_to_user(self.session_id, phone)
        
        # Load full user context (history, appointments, etc.)
        user_context = self._load_user_context(phone)
        
        # Log tool call
        self.db.add_message(
            self.session_id, "tool", f"Identified user: {phone}",
            tool_name="identify_user",
            tool_args={"phone_number": phone_number, "name": name},
            tool_result={
                "phone": phone, 
                "name": self.user_name,
                "is_returning": user_context.get("is_returning", False),
                "appointments_count": len(user_context.get("appointments", {}).get("booked", [])),
            }
        )
        
        # Notify frontend with full context
        await self.send_to_frontend("tool_call", {
            "tool": "identify_user",
            "args": {"phone": phone},
            "result": {
                "success": True, 
                "name": self.user_name,
                "is_returning": user_context.get("is_returning", False),
            }
        })
        
        # Send context loaded event to frontend
        await self.send_to_frontend("context_loaded", {
            "user": {
                "phone": phone,
                "name": self.user_name,
            },
            "is_returning": user_context.get("is_returning", False),
            "total_sessions": user_context.get("total_sessions", 0),
            "appointments": user_context.get("appointments", {}),
            "last_session_summary": user_context.get("last_session", {}).get("summary"),
        })
        
        logger.info(f"User identified: {phone}, returning: {user_context.get('is_returning')}")
        
        # Build personalized response
        return self._build_context_aware_response(user_context)
    
    @function_tool()
    async def fetch_slots(
        self,
        context: RunContext,
        date: Annotated[str | None, "Specific date in YYYY-MM-DD format, or None for next available days"] = None,
    ) -> str:
        """Fetch available appointment slots for booking."""
        slots = []
        try:
            start_date = (
                datetime.strptime(date, "%Y-%m-%d").date() 
                if date else datetime.now().date() + timedelta(days=1)
            )
        except ValueError:
            start_date = datetime.now().date() + timedelta(days=1)
        
        for day_offset in range(5):  # Next 5 days
            slot_date = start_date + timedelta(days=day_offset)
            if slot_date.weekday() >= 5:  # Skip weekends
                continue
            
            date_str = slot_date.strftime("%Y-%m-%d")
            day_name = slot_date.strftime("%A")
            
            for hour in [9, 10, 11, 14, 15, 16]:
                time_str = f"{hour:02d}:00"
                if not self.db.is_slot_booked(date_str, time_str):
                    slots.append({
                        "date": date_str,
                        "day": day_name,
                        "time": time_str,
                        "display": f"{day_name} {date_str} at {hour}:00"
                    })
        
        # Log
        self.db.add_message(
            self.session_id, "tool", f"Fetched {len(slots)} available slots",
            tool_name="fetch_slots",
            tool_args={"date": date},
            tool_result={"slots_count": len(slots)}
        )
        
        await self.send_to_frontend("tool_call", {
            "tool": "fetch_slots",
            "args": {"date": date},
            "result": {"slots": slots[:8]}
        })
        
        if not slots:
            return "No available slots found for the requested period. Would you like to try different dates?"
        
        # Format for voice (limit to 5)
        slot_list = "\n".join([s["display"] for s in slots[:5]])
        more_text = f" ...and {len(slots) - 5} more slots available." if len(slots) > 5 else ""
        
        return f"Here are the available slots:\n{slot_list}{more_text}\n\nWhich one would you like?"
    
    @function_tool()
    async def book_appointment(
        self,
        context: RunContext,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        time: Annotated[str, "Time in HH:MM 24-hour format"],
        notes: Annotated[str | None, "Any notes for the appointment"] = None,
    ) -> str:
        """Book an appointment for the identified user."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        # Check availability
        if self.db.is_slot_booked(date, time):
            await self.send_to_frontend("tool_call", {
                "tool": "book_appointment",
                "args": {"date": date, "time": time},
                "result": {"success": False, "reason": "Slot already booked"}
            })
            return f"Sorry, {date} at {time} is already booked. Would you like a different time?"
        
        # Book it
        appointment = self.db.book_appointment(self.user_phone, date, time, notes=notes)
        
        # Log
        self.db.add_message(
            self.session_id, "tool", f"Booked appointment for {date} at {time}",
            tool_name="book_appointment",
            tool_args={"date": date, "time": time, "notes": notes},
            tool_result={"appointment_id": appointment.get("id"), "status": "booked"}
        )
        
        await self.send_to_frontend("tool_call", {
            "tool": "book_appointment",
            "args": {"date": date, "time": time},
            "result": {"success": True, "appointment": appointment}
        })
        
        logger.info(f"Booked: {self.user_phone} on {date} at {time}")
        return f"Done! Your appointment is confirmed for {date} at {time}. Is there anything else I can help you with?"
    
    @function_tool()
    async def retrieve_appointments(
        self,
        context: RunContext,
    ) -> str:
        """Retrieve user's existing appointments."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        appointments = self.db.get_user_appointments(
            self.user_phone, 
            status=["pending", "booked"]
        )
        
        # Log
        self.db.add_message(
            self.session_id, "tool", f"Retrieved {len(appointments)} appointments",
            tool_name="retrieve_appointments",
            tool_args={},
            tool_result={"count": len(appointments), "appointments": appointments}
        )
        
        await self.send_to_frontend("tool_call", {
            "tool": "retrieve_appointments",
            "args": {},
            "result": {"appointments": appointments}
        })
        
        if not appointments:
            return "You don't have any upcoming appointments. Would you like to book one?"
        
        apt_list = []
        for apt in appointments:
            mentor_info = apt.get("mentors")
            if isinstance(mentor_info, dict):
                mentor_name = mentor_info.get("name", "a consultant")
            else:
                mentor_name = "a consultant"
            apt_list.append(f"{apt['date']} at {apt['time']} with {mentor_name}")
        
        return f"Your upcoming appointments:\n" + "\n".join(apt_list) + "\n\nWould you like to modify or cancel any of these?"
    
    @function_tool()
    async def cancel_appointment(
        self,
        context: RunContext,
        date: Annotated[str, "Date of appointment to cancel (YYYY-MM-DD)"],
        time: Annotated[str, "Time of appointment to cancel (HH:MM)"],
    ) -> str:
        """Cancel an existing appointment."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        success = self.db.cancel_appointment(self.user_phone, date, time)
        
        self.db.add_message(
            self.session_id, "tool", f"Cancel appointment: {date} {time} - {'success' if success else 'not found'}",
            tool_name="cancel_appointment",
            tool_args={"date": date, "time": time},
            tool_result={"success": success}
        )
        
        await self.send_to_frontend("tool_call", {
            "tool": "cancel_appointment",
            "args": {"date": date, "time": time},
            "result": {"success": success}
        })
        
        if success:
            logger.info(f"Cancelled: {self.user_phone} on {date} at {time}")
            return f"Your appointment on {date} at {time} has been cancelled. Is there anything else?"
        else:
            return f"I couldn't find an active appointment on {date} at {time}. Would you like to see your appointments?"
    
    @function_tool()
    async def modify_appointment(
        self,
        context: RunContext,
        old_date: Annotated[str, "Current appointment date (YYYY-MM-DD)"],
        old_time: Annotated[str, "Current appointment time (HH:MM)"],
        new_date: Annotated[str, "New date (YYYY-MM-DD)"],
        new_time: Annotated[str, "New time (HH:MM)"],
    ) -> str:
        """Modify an existing appointment's date and/or time."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        # Check if new slot is available
        if self.db.is_slot_booked(new_date, new_time):
            await self.send_to_frontend("tool_call", {
                "tool": "modify_appointment",
                "args": {"old_date": old_date, "old_time": old_time, "new_date": new_date, "new_time": new_time},
                "result": {"success": False, "reason": "New slot not available"}
            })
            return f"Sorry, {new_date} at {new_time} is not available. Would you like to pick another time?"
        
        result = self.db.modify_appointment(self.user_phone, old_date, old_time, new_date, new_time)
        
        self.db.add_message(
            self.session_id, "tool", 
            f"Modify appointment: {old_date} {old_time} → {new_date} {new_time}",
            tool_name="modify_appointment",
            tool_args={"old_date": old_date, "old_time": old_time, "new_date": new_date, "new_time": new_time},
            tool_result={"success": bool(result)}
        )
        
        await self.send_to_frontend("tool_call", {
            "tool": "modify_appointment",
            "args": {"old_date": old_date, "old_time": old_time, "new_date": new_date, "new_time": new_time},
            "result": {"success": bool(result), "appointment": result}
        })
        
        if result:
            logger.info(f"Modified: {self.user_phone} from {old_date} {old_time} to {new_date} {new_time}")
            return f"Your appointment has been moved from {old_date} at {old_time} to {new_date} at {new_time}. Anything else?"
        else:
            return f"I couldn't find your appointment on {old_date} at {old_time}. Would you like to see your appointments?"
    
    @function_tool()
    async def end_conversation(
        self,
        context: RunContext,
    ) -> str:
        """End the conversation, generate summary, and display cost breakdown."""
        # Get session messages for summary
        messages = self.db.get_session_messages(self.session_id)
        
        # Get user's current appointments
        appointments = []
        if self.user_phone:
            appointments = self.db.get_user_appointments(self.user_phone, status="booked")
        
        # Generate summary from tool calls
        actions_taken = [m for m in messages if m.get("role") == "tool" and m.get("tool_name")]
        summary_parts = []
        
        for msg in actions_taken:
            tool = msg.get("tool_name")
            result = msg.get("tool_result", {}) or {}
            args = msg.get("tool_args", {}) or {}
            
            if tool == "book_appointment" and result.get("success"):
                summary_parts.append(f"Booked appointment for {args.get('date')} at {args.get('time')}")
            elif tool == "cancel_appointment" and result.get("success"):
                summary_parts.append(f"Cancelled appointment for {args.get('date')} at {args.get('time')}")
            elif tool == "modify_appointment" and result.get("success"):
                summary_parts.append(f"Moved appointment from {args.get('old_date')} to {args.get('new_date')}")
        
        # Calculate cost
        cost = self.calculate_cost()
        
        summary_text = "; ".join(summary_parts) if summary_parts else "No changes made"
        
        # Build full summary
        full_summary = {
            "user_phone": self.user_phone,
            "user_name": self.user_name,
            "actions": summary_parts,
            "upcoming_appointments": [
                {"date": apt["date"], "time": apt["time"]}
                for apt in appointments
            ],
            "cost_breakdown": cost
        }
        
        # Save session
        self.db.end_session(
            self.session_id,
            contact_number=self.user_phone,
            summary=summary_text,
            cost_breakdown=cost
        )
        
        # Send summary to frontend
        await self.send_to_frontend("summary", full_summary)
        
        await self.send_to_frontend("tool_call", {
            "tool": "end_conversation",
            "args": {},
            "result": {"summary": full_summary}
        })
        
        logger.info(f"Session ended: {self.session_id}, summary: {summary_text}")
        
        # Build voice response
        response = "Here's a summary of our conversation: "
        if summary_parts:
            response += ". ".join(summary_parts) + ". "
        else:
            response += "We discussed your appointments. "
        
        if appointments:
            response += f"You have {len(appointments)} upcoming appointment{'s' if len(appointments) > 1 else ''}. "
        
        response += f"The estimated cost for this call was ${cost['total']:.4f}. "
        response += "Thank you for using SuperBryn! Have a great day!"
        
        return response


async def entrypoint(ctx: JobContext):
    """
    LiveKit Agent entrypoint.
    
    LiveKit handles session management - we just track it in our database.
    Each room connection creates a new session that gets linked to a user
    once they're identified.
    """
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Initialize database
    db = Database()
    
    # Create a new session in our database (linked to LiveKit room)
    session_record = db.create_session(room_name=ctx.room.name)
    session_id = session_record["id"]
    
    logger.info(f"Session created: {session_id} for room: {ctx.room.name}")
    
    # Create agent with room and database references
    agent = VoiceAgent(room=ctx.room, db=db, session_id=session_id)
    
    # Create LiveKit AgentSession with all components
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
    
    # Track user transcripts
    @session.on("user_speech_committed")
    async def on_user_speech(ev):
        text = getattr(ev, 'text', '') or getattr(ev, 'transcript', '')
        if text:
            db.add_message(session_id, "user", text)
            await agent.send_to_frontend("transcript", {"role": "user", "text": text})
            # Estimate STT cost (rough: average speaking rate is ~150 words/min)
            agent.cost_tracker["stt_minutes"] += len(text.split()) / 150
    
    # Track agent responses
    @session.on("agent_speech_committed")
    async def on_agent_speech(ev):
        text = getattr(ev, 'text', '') or getattr(ev, 'transcript', '')
        if text:
            db.add_message(session_id, "assistant", text)
            await agent.send_to_frontend("transcript", {"role": "assistant", "text": text})
            # Estimate TTS cost
            agent.cost_tracker["tts_characters"] += len(text)
    
    # Start session
    await session.start(agent=agent, room=ctx.room)
    
    # Initial greeting
    await session.say(
        "Hello! I'm your SuperBryn appointment assistant. "
        "To get started, could you please tell me your phone number?"
    )
    
    logger.info(f"Agent ready for session: {session_id}")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
