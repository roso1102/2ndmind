-- 🗄️ Supabase Schema for MySecondMind User Management
-- This SQL script creates the required table structure for user data storage

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    telegram_username TEXT,
    first_name TEXT,
    last_name TEXT,
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
-- Note: Adjust based on your authentication strategy in production
CREATE POLICY "Users can manage their own data" ON users
    FOR ALL
    USING (true);

-- Grant necessary permissions (adjust for your auth setup)
GRANT ALL ON users TO authenticated;
GRANT ALL ON users TO anon;

-- Comments for documentation
COMMENT ON TABLE users IS 'Stores user registration data and metadata';
COMMENT ON COLUMN users.user_id IS 'Telegram user ID (primary identifier)';
COMMENT ON COLUMN users.telegram_username IS 'Telegram username for reference';
COMMENT ON COLUMN users.first_name IS 'User first name (optional)';
COMMENT ON COLUMN users.last_name IS 'User last name (optional)';
COMMENT ON COLUMN users.created_at IS 'User registration timestamp';
COMMENT ON COLUMN users.last_active IS 'Last activity timestamp';
COMMENT ON COLUMN users.is_active IS 'Soft delete flag';
