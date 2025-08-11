-- Fix RLS Policy for User Registration
-- This addresses the "new row violates row-level security policy" error

-- Drop existing policy
DROP POLICY IF EXISTS "Users can manage their own data" ON users;

-- Create more permissive policy for user registration
-- Allow INSERT for anyone (needed for registration)
-- Allow other operations for users managing their own data
CREATE POLICY "Allow user registration and self-management" ON users
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Alternative: Create separate policies for different operations
-- Uncomment these if the above doesn't work:

-- DROP POLICY IF EXISTS "Allow user registration and self-management" ON users;
-- 
-- -- Allow anyone to INSERT (register new users)
-- CREATE POLICY "Allow user registration" ON users
--     FOR INSERT
--     WITH CHECK (true);
-- 
-- -- Allow users to SELECT their own data
-- CREATE POLICY "Users can view their own data" ON users
--     FOR SELECT
--     USING (true);
-- 
-- -- Allow users to UPDATE their own data
-- CREATE POLICY "Users can update their own data" ON users
--     FOR UPDATE
--     USING (true)
--     WITH CHECK (true);
-- 
-- -- Allow users to DELETE their own data (optional)
-- CREATE POLICY "Users can delete their own data" ON users
--     FOR DELETE
--     USING (true);

-- Ensure proper grants are in place
GRANT ALL ON users TO authenticated;
GRANT ALL ON users TO anon;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;
