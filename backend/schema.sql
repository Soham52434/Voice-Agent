-- ================================================
-- SUPABASE SCHEMA FOR VOICE AGENT
-- Complete schema with users, mentors, availability, sessions, admin
-- Run this in your Supabase SQL Editor
-- ================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==================== USERS ====================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_number TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL DEFAULT 'User',
    email TEXT,
    password_hash TEXT, -- Optional: for web login
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_phone ON users(contact_number);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- ==================== MENTORS ====================
CREATE TABLE IF NOT EXISTS mentors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    password_hash TEXT NOT NULL,
    specialty TEXT,
    bio TEXT,
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mentors_email ON mentors(email);
CREATE INDEX IF NOT EXISTS idx_mentors_active ON mentors(is_active);

-- Insert default mentors with password 'mentor123'
INSERT INTO mentors (name, email, password_hash, specialty) 
SELECT 'Dr. Sarah Smith', 'sarah@example.com', crypt('mentor123', gen_salt('bf')), 'General Consultation'
WHERE NOT EXISTS (SELECT 1 FROM mentors WHERE email = 'sarah@example.com');

INSERT INTO mentors (name, email, password_hash, specialty) 
SELECT 'Dr. John Doe', 'john@example.com', crypt('mentor123', gen_salt('bf')), 'Technical Review'
WHERE NOT EXISTS (SELECT 1 FROM mentors WHERE email = 'john@example.com');

-- ==================== MENTOR AVAILABILITY ====================
-- Stores when mentors are available for bookings
CREATE TABLE IF NOT EXISTS mentor_availability (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mentor_id UUID NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration_minutes INT DEFAULT 60, -- Duration of each slot
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate availability entries
    UNIQUE(mentor_id, date, start_time)
);

CREATE INDEX IF NOT EXISTS idx_availability_mentor ON mentor_availability(mentor_id, date);
CREATE INDEX IF NOT EXISTS idx_availability_date ON mentor_availability(date, is_available);

-- ==================== APPOINTMENTS ====================
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    mentor_id UUID REFERENCES mentors(id) ON DELETE SET NULL,
    contact_number TEXT NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    duration_minutes INT DEFAULT 60,
    status TEXT NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'booked', 'completed', 'cancelled', 'no_show')),
    notes TEXT,
    user_notes TEXT, -- Notes from user
    mentor_notes TEXT, -- Notes from mentor
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_user ON appointments(contact_number, status);
CREATE INDEX IF NOT EXISTS idx_appointments_mentor ON appointments(mentor_id, date, status);
CREATE INDEX IF NOT EXISTS idx_appointments_slot ON appointments(date, time, status);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);

-- ==================== SESSIONS (Voice Conversations) ====================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_name TEXT NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    contact_number TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_seconds INT,
    summary TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    cost_breakdown JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(contact_number);
CREATE INDEX IF NOT EXISTS idx_sessions_ended ON sessions(contact_number, ended_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_room ON sessions(room_name);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

-- ==================== SESSION MESSAGES ====================
CREATE TABLE IF NOT EXISTS session_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_name TEXT,
    tool_args JSONB,
    tool_result JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON session_messages(session_id, timestamp);

-- ==================== ADMINS ====================
CREATE TABLE IF NOT EXISTS admins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'admin' CHECK (role IN ('admin', 'super_admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Insert default admin with password 'admin123'
INSERT INTO admins (email, name, password_hash, role) 
SELECT 'admin@superbryn.com', 'Super Admin', crypt('admin123', gen_salt('bf')), 'super_admin'
WHERE NOT EXISTS (SELECT 1 FROM admins WHERE email = 'admin@superbryn.com');

-- ==================== COST TRACKING ====================
-- Aggregated cost data for admin dashboard
CREATE TABLE IF NOT EXISTS cost_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    service TEXT NOT NULL CHECK (service IN ('deepgram_stt', 'cartesia_tts', 'openai_llm', 'livekit')),
    units DECIMAL(10, 4) NOT NULL, -- Minutes, characters, tokens, etc.
    unit_type TEXT NOT NULL, -- 'minutes', 'characters', 'tokens'
    cost_usd DECIMAL(10, 6) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cost_logs_session ON cost_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_cost_logs_service ON cost_logs(service, created_at);

-- ==================== ROW LEVEL SECURITY ====================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentors ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentor_availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_logs ENABLE ROW LEVEL SECURITY;

-- Policies (allow all for service role - tighten in production)
DO $$ 
BEGIN
    DROP POLICY IF EXISTS "Allow all users" ON users;
    DROP POLICY IF EXISTS "Allow all mentors" ON mentors;
    DROP POLICY IF EXISTS "Allow all mentor_availability" ON mentor_availability;
    DROP POLICY IF EXISTS "Allow all appointments" ON appointments;
    DROP POLICY IF EXISTS "Allow all sessions" ON sessions;
    DROP POLICY IF EXISTS "Allow all session_messages" ON session_messages;
    DROP POLICY IF EXISTS "Allow all admins" ON admins;
    DROP POLICY IF EXISTS "Allow all cost_logs" ON cost_logs;
    
    CREATE POLICY "Allow all users" ON users FOR ALL USING (true);
    CREATE POLICY "Allow all mentors" ON mentors FOR ALL USING (true);
    CREATE POLICY "Allow all mentor_availability" ON mentor_availability FOR ALL USING (true);
    CREATE POLICY "Allow all appointments" ON appointments FOR ALL USING (true);
    CREATE POLICY "Allow all sessions" ON sessions FOR ALL USING (true);
    CREATE POLICY "Allow all session_messages" ON session_messages FOR ALL USING (true);
    CREATE POLICY "Allow all admins" ON admins FOR ALL USING (true);
    CREATE POLICY "Allow all cost_logs" ON cost_logs FOR ALL USING (true);
END $$;

-- ==================== VIEWS ====================

-- View for appointment calendar (mentor dashboard)
CREATE OR REPLACE VIEW appointment_calendar AS
SELECT 
    a.id,
    a.date,
    a.time,
    a.duration_minutes,
    a.status,
    a.notes,
    a.mentor_notes,
    u.name as user_name,
    u.contact_number as user_phone,
    m.id as mentor_id,
    m.name as mentor_name
FROM appointments a
LEFT JOIN users u ON a.user_id = u.id
LEFT JOIN mentors m ON a.mentor_id = m.id
WHERE a.status IN ('pending', 'booked', 'completed')
ORDER BY a.date, a.time;

-- View for admin cost summary
CREATE OR REPLACE VIEW cost_summary AS
SELECT 
    DATE_TRUNC('day', cl.created_at) as date,
    cl.service,
    SUM(cl.units) as total_units,
    cl.unit_type,
    SUM(cl.cost_usd) as total_cost,
    COUNT(DISTINCT cl.session_id) as session_count
FROM cost_logs cl
GROUP BY DATE_TRUNC('day', cl.created_at), cl.service, cl.unit_type
ORDER BY date DESC, service;

-- ==================== HELPER FUNCTIONS ====================

-- Function to get available slots for a mentor on a date
CREATE OR REPLACE FUNCTION get_mentor_available_slots(
    p_mentor_id UUID,
    p_date DATE
)
RETURNS TABLE (
    slot_time TIME,
    is_booked BOOLEAN
) AS $$
DECLARE
    v_start_time TIME;
    v_end_time TIME;
    v_slot_duration INT;
    v_current_time TIME;
BEGIN
    -- Get availability for the date
    SELECT start_time, end_time, slot_duration_minutes
    INTO v_start_time, v_end_time, v_slot_duration
    FROM mentor_availability
    WHERE mentor_id = p_mentor_id 
      AND date = p_date 
      AND is_available = TRUE
    LIMIT 1;
    
    IF v_start_time IS NULL THEN
        RETURN;
    END IF;
    
    v_current_time := v_start_time;
    
    WHILE v_current_time < v_end_time LOOP
        RETURN QUERY
        SELECT 
            v_current_time,
            EXISTS (
                SELECT 1 FROM appointments 
                WHERE mentor_id = p_mentor_id 
                  AND date = p_date 
                  AND time = v_current_time 
                  AND status IN ('pending', 'booked')
            );
        v_current_time := v_current_time + (v_slot_duration || ' minutes')::INTERVAL;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to check if appointment time has passed (for status update)
CREATE OR REPLACE FUNCTION check_completed_appointments()
RETURNS void AS $$
BEGIN
    UPDATE appointments
    SET status = 'completed', updated_at = NOW()
    WHERE status = 'booked'
      AND (date < CURRENT_DATE OR (date = CURRENT_DATE AND time < CURRENT_TIME));
END;
$$ LANGUAGE plpgsql;

-- Function to get admin dashboard stats
CREATE OR REPLACE FUNCTION get_admin_stats()
RETURNS TABLE (
    total_users BIGINT,
    total_mentors BIGINT,
    total_sessions BIGINT,
    active_sessions BIGINT,
    total_appointments BIGINT,
    pending_appointments BIGINT,
    completed_appointments BIGINT,
    total_cost DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM users WHERE is_active = TRUE),
        (SELECT COUNT(*) FROM mentors WHERE is_active = TRUE),
        (SELECT COUNT(*) FROM sessions),
        (SELECT COUNT(*) FROM sessions WHERE status = 'active'),
        (SELECT COUNT(*) FROM appointments),
        (SELECT COUNT(*) FROM appointments WHERE status = 'pending'),
        (SELECT COUNT(*) FROM appointments WHERE status = 'completed'),
        (SELECT COALESCE(SUM(cost_usd), 0) FROM cost_logs);
END;
$$ LANGUAGE plpgsql;
