-- 🗄️ Supabase Schema for MySecondMind User Management
-- This SQL script creates the required table structure for user data storage

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    telegram_username TEXT,
    encrypted_notion_token TEXT,
    db_notes TEXT,
    db_links TEXT,
    db_reminders TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_active ON users(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policy to allow users to manage their own data
-- Note: This is a basic policy. You may want to customize based on your security needs.
CREATE POLICY "Users can manage their own data" ON users
    FOR ALL
    USING (true);  -- Adjust this based on your authentication strategy

-- Grant necessary permissions
GRANT ALL ON users TO authenticated;
GRANT ALL ON users TO anon;

-- Comments for documentation
COMMENT ON TABLE users IS 'Stores user registration data and encrypted Notion tokens';
COMMENT ON COLUMN users.user_id IS 'Telegram user ID (primary identifier)';
COMMENT ON COLUMN users.telegram_username IS 'Telegram username for reference';
COMMENT ON COLUMN users.encrypted_notion_token IS 'Fernet-encrypted Notion API token';
COMMENT ON COLUMN users.db_notes IS 'Notion database ID for notes';
COMMENT ON COLUMN users.db_links IS 'Notion database ID for links';
COMMENT ON COLUMN users.db_reminders IS 'Notion database ID for reminders';
COMMENT ON COLUMN users.created_at IS 'User registration timestamp';
COMMENT ON COLUMN users.last_active IS 'Last activity timestamp';
COMMENT ON COLUMN users.is_active IS 'Soft delete flag';
