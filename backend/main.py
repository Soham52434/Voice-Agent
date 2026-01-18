"""
Voice Agent - Minimal Implementation using LiveKit's Native Plugins

This uses LiveKit's official plugins for:
- Deepgram STT (speech-to-text)
- Cartesia TTS (text-to-speech)  
- OpenAI LLM (language model)
- Silero VAD (voice activity detection)

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")


class VoiceAgent(Agent):
    """
    Appointment booking voice agent.
    
    LiveKit handles the entire voice pipeline:
    Audio → VAD → STT → LLM (with tools) → TTS → Audio
    
    We just define tools and let LiveKit orchestrate everything.
    """
    
    def __init__(self):
        super().__init__(
            instructions="""You are a friendly appointment booking assistant. 

Your workflow:
1. Greet the user warmly
2. Ask for their phone number to identify them
3. Help them book, view, modify, or cancel appointments
4. When they're done, summarize what was accomplished and say goodbye

Guidelines:
- Be conversational and natural
- Confirm details before booking
- If a slot is taken, suggest alternatives
- Keep responses concise (this is voice, not text)
""",
        )
        self.db = Database()
        self.user_phone: str | None = None
        self.conversation_log: list[dict] = []
    
    # ==================== TOOLS ====================
    # LiveKit automatically:
    # 1. Converts these to OpenAI function schemas
    # 2. Calls them when the LLM decides to
    # 3. Feeds the result back to the LLM
    
    @function_tool()
    async def lookup_user(
        self,
        context: RunContext,
        phone_number: Annotated[str, "User's phone number, digits only (e.g., 1234567890)"],
    ) -> str:
        """Look up or register a user by their phone number."""
        # Normalize phone number
        phone = "".join(filter(str.isdigit, phone_number))
        if len(phone) == 10:
            phone = f"+1{phone}"
        elif not phone.startswith("+"):
            phone = f"+{phone}"
        
        user = self.db.get_or_create_user(phone)
        self.user_phone = phone
        
        logger.info(f"User identified: {phone}")
        return f"Found user with phone {phone}. Name: {user.get('name', 'Unknown')}"
    
    @function_tool()
    async def get_available_slots(
        self,
        context: RunContext,
        date: Annotated[str | None, "Optional date in YYYY-MM-DD format. If not provided, shows next 3 days."] = None,
    ) -> str:
        """Get available appointment slots."""
        # Generate slots for next few days
        slots = []
        start_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date() + timedelta(days=1)
        
        for day_offset in range(3):
            slot_date = start_date + timedelta(days=day_offset)
            if slot_date.weekday() >= 5:  # Skip weekends
                continue
            
            date_str = slot_date.strftime("%Y-%m-%d")
            for hour in [9, 10, 11, 14, 15, 16]:
                time_str = f"{hour:02d}:00"
                if not self.db.is_slot_booked(date_str, time_str):
                    slots.append(f"{date_str} at {time_str}")
        
        if not slots:
            return "No available slots found. Try a different date range."
        
        return f"Available slots:\n" + "\n".join(slots[:8])  # Limit for voice
    
    @function_tool()
    async def book_appointment(
        self,
        context: RunContext,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        time: Annotated[str, "Time in HH:MM 24-hour format (e.g., 14:00)"],
    ) -> str:
        """Book an appointment for the identified user."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        # Check availability
        if self.db.is_slot_booked(date, time):
            return f"Sorry, {date} at {time} is already booked. Would you like a different time?"
        
        # Book it
        appointment = self.db.book_appointment(self.user_phone, date, time)
        
        self.conversation_log.append({
            "action": "booked",
            "date": date,
            "time": time,
        })
        
        logger.info(f"Booked appointment: {self.user_phone} on {date} at {time}")
        return f"Done! Your appointment is confirmed for {date} at {time}."
    
    @function_tool()
    async def get_my_appointments(
        self,
        context: RunContext,
    ) -> str:
        """Get the user's existing appointments."""
        if not self.user_phone:
            return "I need to identify you first. What's your phone number?"
        
        appointments = self.db.get_user_appointments(self.user_phone)
        
        if not appointments:
            return "You don't have any upcoming appointments."
        
        apt_list = [f"{apt['date']} at {apt['time']}" for apt in appointments]
        return f"Your appointments:\n" + "\n".join(apt_list)
    
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
        
        if success:
            self.conversation_log.append({
                "action": "cancelled",
                "date": date,
                "time": time,
            })
            logger.info(f"Cancelled appointment: {self.user_phone} on {date} at {time}")
            return f"Your appointment on {date} at {time} has been cancelled."
        else:
            return f"I couldn't find an appointment on {date} at {time}."
    
    @function_tool()
    async def end_call(
        self,
        context: RunContext,
    ) -> str:
        """End the conversation and provide a summary."""
        summary_parts = []
        
        for log in self.conversation_log:
            if log["action"] == "booked":
                summary_parts.append(f"Booked: {log['date']} at {log['time']}")
            elif log["action"] == "cancelled":
                summary_parts.append(f"Cancelled: {log['date']} at {log['time']}")
        
        # Save to database
        if self.user_phone:
            summary_text = "; ".join(summary_parts) if summary_parts else "No changes made"
            self.db.save_conversation(self.user_phone, summary_text, self.conversation_log)
        
        if summary_parts:
            return f"Summary of today's call: {'; '.join(summary_parts)}. Thank you, have a great day!"
        else:
            return "Thank you for calling! Have a great day!"


async def entrypoint(ctx: JobContext):
    """
    LiveKit Agent entrypoint.
    
    This is called when a user joins a room. LiveKit handles:
    - WebRTC connection
    - Audio streaming
    - The entire STT → LLM → TTS pipeline
    """
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Create the voice pipeline using official LiveKit plugins
    session = AgentSession(
        # Voice Activity Detection - detects when user starts/stops speaking
        vad=silero.VAD.load(),
        
        # Speech-to-Text - Deepgram Nova-2 with streaming
        stt=deepgram.STT(
            model="nova-2",
            language="en-US",
        ),
        
        # Language Model - handles conversation and tool calling
        llm=openai.LLM(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        ),
        
        # Text-to-Speech - Cartesia with natural voice
        tts=cartesia.TTS(
            model="sonic-2",
            voice=os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091"),
            language="en",
        ),
        
        # Allow user to interrupt the agent
        allow_interruptions=True,
    )
    
    # Create agent and start
    agent = VoiceAgent()
    await session.start(agent=agent, room=ctx.room)
    
    # Initial greeting
    await session.say("Hello! I'm your appointment assistant. How can I help you today?")
    
    logger.info("Agent session started")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
