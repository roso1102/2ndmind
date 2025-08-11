-- ============================================================================
-- MySecondMind Advanced Features Schema
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector" CASCADE;

-- ============================================================================
-- 1. CONVERSATION MEMORY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    message_text TEXT NOT NULL,
    response_text TEXT,
    intent VARCHAR(50),
    confidence FLOAT,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to users table
    CONSTRAINT fk_conversation_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE
);

-- Index for fast conversation retrieval
CREATE INDEX IF NOT EXISTS idx_conversation_user_time 
    ON conversation_history(user_id, created_at DESC);

-- ============================================================================
-- 2. NOTIFICATIONS & SCHEDULING TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    content_id UUID, -- Optional link to content
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'reminder', -- reminder, task, morning_brief, memory_resurface
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    recurring_pattern VARCHAR(100), -- daily, weekly, monthly, etc.
    is_sent BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Foreign key to users table
    CONSTRAINT fk_notification_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE,
    
    -- Optional foreign key to content
    CONSTRAINT fk_notification_content 
        FOREIGN KEY (content_id) 
        REFERENCES user_content(id) 
        ON DELETE SET NULL
);

-- Indexes for scheduling queries
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled 
    ON notifications(scheduled_time) 
    WHERE is_active = TRUE AND is_sent = FALSE;

CREATE INDEX IF NOT EXISTS idx_notifications_user_type 
    ON notifications(user_id, notification_type, created_at DESC);

-- ============================================================================
-- 3. CONTENT EMBEDDINGS TABLE (for semantic search)
-- ============================================================================
CREATE TABLE IF NOT EXISTS content_embeddings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    content_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    embedding vector(384), -- sentence-transformers all-MiniLM-L6-v2 size
    model_name VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    CONSTRAINT fk_embedding_content 
        FOREIGN KEY (content_id) 
        REFERENCES user_content(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_embedding_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE,
    
    -- Unique constraint to prevent duplicate embeddings
    UNIQUE(content_id, model_name)
);

-- Index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
    ON content_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_embeddings_user 
    ON content_embeddings(user_id);

-- ============================================================================
-- 4. USER PREFERENCES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    timezone VARCHAR(50) DEFAULT 'UTC',
    morning_brief_time TIME DEFAULT '08:00',
    evening_summary_time TIME DEFAULT '20:00',
    notification_frequency VARCHAR(20) DEFAULT 'normal', -- low, normal, high
    memory_resurface_frequency VARCHAR(20) DEFAULT 'weekly', -- daily, weekly, monthly
    preferred_language VARCHAR(10) DEFAULT 'en',
    ai_personality VARCHAR(50) DEFAULT 'helpful', -- helpful, casual, professional
    search_preferences JSONB DEFAULT '{}',
    notification_settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to users table
    CONSTRAINT fk_preferences_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE
);

-- ============================================================================
-- 5. MEMORY RESURFACING TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_resurface_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    content_id UUID NOT NULL,
    resurface_type VARCHAR(50) NOT NULL, -- daily_summary, random_memory, spaced_repetition
    resurface_date DATE NOT NULL,
    user_engagement VARCHAR(20), -- viewed, clicked, ignored, saved_again
    engagement_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    CONSTRAINT fk_resurface_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_resurface_content 
        FOREIGN KEY (content_id) 
        REFERENCES user_content(id) 
        ON DELETE CASCADE,
    
    -- Unique constraint to prevent duplicate resurfacing on same day
    UNIQUE(user_id, content_id, resurface_date, resurface_type)
);

-- Index for resurfacing queries
CREATE INDEX IF NOT EXISTS idx_resurface_user_date 
    ON memory_resurface_log(user_id, resurface_date DESC);

CREATE INDEX IF NOT EXISTS idx_resurface_engagement 
    ON memory_resurface_log(content_id, engagement_score DESC);

-- ============================================================================
-- 6. ANALYTICS & USAGE TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS usage_analytics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- save_note, search, complete_task, etc.
    content_type VARCHAR(50), -- note, task, link, reminder
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to users table
    CONSTRAINT fk_analytics_user 
        FOREIGN KEY (user_id) 
        REFERENCES users(user_id) 
        ON DELETE CASCADE
);

-- Index for analytics queries
CREATE INDEX IF NOT EXISTS idx_analytics_user_action 
    ON usage_analytics(user_id, action_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analytics_content_type 
    ON usage_analytics(content_type, created_at DESC);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_content_embeddings_updated_at ON content_embeddings;
CREATE TRIGGER update_content_embeddings_updated_at
    BEFORE UPDATE ON content_embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON user_preferences;
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create user preferences on user creation
CREATE OR REPLACE FUNCTION create_default_user_preferences()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_preferences (user_id) 
    VALUES (NEW.user_id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to create default preferences for new users
DROP TRIGGER IF EXISTS create_user_preferences_trigger ON users;
CREATE TRIGGER create_user_preferences_trigger
    AFTER INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION create_default_user_preferences();

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all new tables
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_resurface_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_analytics ENABLE ROW LEVEL SECURITY;

-- Policies: Users can only access their own data
DROP POLICY IF EXISTS "Users can manage their own conversation history" ON conversation_history;
CREATE POLICY "Users can manage their own conversation history" ON conversation_history
    FOR ALL USING (user_id = current_setting('app.current_user_id')::text);

DROP POLICY IF EXISTS "Users can manage their own notifications" ON notifications;
CREATE POLICY "Users can manage their own notifications" ON notifications
    FOR ALL USING (user_id = current_setting('app.current_user_id')::text);

DROP POLICY IF EXISTS "Users can manage their own embeddings" ON content_embeddings;
CREATE POLICY "Users can manage their own embeddings" ON content_embeddings
    FOR ALL USING (user_id = current_setting('app.current_user_id')::text);

DROP POLICY IF EXISTS "Users can manage their own preferences" ON user_preferences;
CREATE POLICY "Users can manage their own preferences" ON user_preferences
    FOR ALL USING (user_id = current_setting('app.current_user_id')::text);

DROP POLICY IF EXISTS "Users can manage their own resurface log" ON memory_resurface_log;
CREATE POLICY "Users can manage their own resurface log" ON memory_resurface_log
    FOR ALL USING (user_id = current_setting('app.current_user_id')::text);

DROP POLICY IF EXISTS "Users can manage their own analytics" ON usage_analytics;
CREATE POLICY "Users can manage their own analytics" ON usage_analytics
    FOR ALL USING (user_id = current_setting('app.current_user_id')::text);

-- ============================================================================
-- HELPFUL FUNCTIONS FOR THE APP
-- ============================================================================

-- Function to get user's timezone
CREATE OR REPLACE FUNCTION get_user_timezone(p_user_id TEXT)
RETURNS VARCHAR(50) AS $$
DECLARE
    user_tz VARCHAR(50);
BEGIN
    SELECT timezone INTO user_tz 
    FROM user_preferences 
    WHERE user_id = p_user_id;
    
    RETURN COALESCE(user_tz, 'UTC');
END;
$$ LANGUAGE plpgsql;

-- Function to get pending notifications
CREATE OR REPLACE FUNCTION get_pending_notifications(p_limit INTEGER DEFAULT 100)
RETURNS TABLE(
    id UUID,
    user_id TEXT,
    title VARCHAR(500),
    message TEXT,
    notification_type VARCHAR(50),
    scheduled_time TIMESTAMP WITH TIME ZONE,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT n.id, n.user_id, n.title, n.message, n.notification_type, 
           n.scheduled_time, n.metadata
    FROM notifications n
    WHERE n.is_active = TRUE 
      AND n.is_sent = FALSE 
      AND n.scheduled_time <= CURRENT_TIMESTAMP
    ORDER BY n.scheduled_time ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to mark notification as sent
CREATE OR REPLACE FUNCTION mark_notification_sent(p_notification_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE notifications 
    SET is_sent = TRUE, sent_at = CURRENT_TIMESTAMP
    WHERE id = p_notification_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA INSERTION (for testing)
-- ============================================================================

-- This will be populated when users start using the advanced features
-- No sample data needed for production

-- ============================================================================
-- SCHEMA COMPLETE
-- ============================================================================
