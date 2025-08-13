-- 🗄️ Supabase Content Schema for MySecondMind
-- This extends the existing user management schema with content storage

-- Create unified content table for all user content
CREATE TABLE IF NOT EXISTS user_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Content classification
    content_type TEXT CHECK (content_type IN ('note', 'link', 'task', 'reminder', 'file')) NOT NULL,
    
    -- Basic content fields
    title TEXT,
    content TEXT NOT NULL,
    
    -- Link-specific fields
    url TEXT,
    url_title TEXT,
    
    -- Task/reminder specific fields
    completed BOOLEAN DEFAULT FALSE,
    due_date TIMESTAMP WITH TIME ZONE,
    priority TEXT CHECK (priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
    
    -- File-specific fields
    file_url TEXT,
    file_type TEXT,
    file_size INTEGER,
    
    -- Organization
    tags TEXT[],
    category TEXT,
    
    -- AI classification metadata
    ai_confidence REAL,
    ai_reasoning TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Search optimization (populated by trigger)
    search_vector tsvector
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_content_user_id ON user_content(user_id);
CREATE INDEX IF NOT EXISTS idx_user_content_type ON user_content(content_type);
CREATE INDEX IF NOT EXISTS idx_user_content_created ON user_content(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_content_due_date ON user_content(due_date) WHERE due_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_user_content_tags ON user_content USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_user_content_search ON user_content USING GIN(search_vector);

-- Enable Row Level Security
ALTER TABLE user_content ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can manage their own content" ON user_content
    FOR ALL
    USING (true);  -- Adjust based on your auth strategy

-- Grant permissions
GRANT ALL ON user_content TO authenticated;
GRANT ALL ON user_content TO anon;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create function to update search vector
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', 
        COALESCE(NEW.title, '') || ' ' || 
        COALESCE(NEW.content, '') || ' ' || 
        COALESCE(NEW.url_title, '') || ' ' ||
        COALESCE(array_to_string(NEW.tags, ' '), '')
    );
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_user_content_updated_at 
    BEFORE UPDATE ON user_content 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create trigger for search vector
CREATE TRIGGER update_user_content_search_vector
    BEFORE INSERT OR UPDATE ON user_content
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

-- Create view for easy content querying
CREATE OR REPLACE VIEW user_content_summary AS
SELECT 
    user_id,
    content_type,
    COUNT(*) as count,
    MAX(created_at) as last_created
FROM user_content 
GROUP BY user_id, content_type;

-- Grant access to view
GRANT SELECT ON user_content_summary TO authenticated;
GRANT SELECT ON user_content_summary TO anon;

-- Comments for documentation
COMMENT ON TABLE user_content IS 'Unified storage for all user content (notes, links, tasks, reminders, files)';
COMMENT ON COLUMN user_content.user_id IS 'Reference to user from users table';
COMMENT ON COLUMN user_content.content_type IS 'Type of content: note, link, task, reminder, file';
COMMENT ON COLUMN user_content.search_vector IS 'Auto-generated full-text search vector';
COMMENT ON COLUMN user_content.ai_confidence IS 'AI classification confidence (0.0-1.0)';

-- ===============================
-- Conversation Memory Extensions
-- ===============================

-- Per-message conversation history
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    conversation_id TEXT DEFAULT 'default',
    role TEXT CHECK (role IN ('user','assistant')) NOT NULL,
    content TEXT NOT NULL,
    intent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conv_hist_user ON conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_hist_conv ON conversation_history(user_id, conversation_id, created_at DESC);

ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their conversation history" ON conversation_history
    FOR ALL USING (true);
GRANT ALL ON conversation_history TO authenticated;
GRANT ALL ON conversation_history TO anon;

-- Rolling conversation summaries per user/conversation
CREATE TABLE IF NOT EXISTS conversation_summaries (
    user_id TEXT PRIMARY KEY,
    conversation_id TEXT DEFAULT 'default',
    summary TEXT,
    awaiting_followup BOOLEAN DEFAULT FALSE,
    followup_context JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their conversation summaries" ON conversation_summaries
    FOR ALL USING (true);
GRANT ALL ON conversation_summaries TO authenticated;
GRANT ALL ON conversation_summaries TO anon;

CREATE OR REPLACE FUNCTION update_conv_summary_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_update_conv_summary_updated_at
    BEFORE UPDATE ON conversation_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_conv_summary_updated_at();