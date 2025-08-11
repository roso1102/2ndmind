# 🗄️ Supabase Setup Guide for MySecondMind

This guide will help you set up Supabase as the database backend for MySecondMind user management.

## 📋 Prerequisites

- A Supabase account (sign up at [supabase.com](https://supabase.com))
- Basic familiarity with SQL

## 🚀 Step-by-Step Setup

### 1. Create a New Supabase Project

1. Log in to your Supabase dashboard
2. Click "New Project"
3. Choose your organization
4. Enter project details:
   - **Name**: `MySecondMind` (or your preferred name)
   - **Database Password**: Generate a strong password and save it
   - **Region**: Choose the region closest to your users
5. Click "Create new project"

### 2. Get Your Project Credentials

1. Go to your project dashboard
2. Navigate to **Settings** → **API**
3. Copy the following values:
   - **Project URL**: Your `SUPABASE_URL`
   - **anon public key**: Your `SUPABASE_ANON_KEY`

### 3. Set Up the Database Schema

1. In your Supabase dashboard, go to **SQL Editor**
2. Create a new query
3. Copy and paste the contents of `supabase_schema.sql` from this repository
4. Click "Run" to execute the schema

### 4. Configure Environment Variables

1. Create a `.env` file
2. Add your Supabase credentials:
   ```bash
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   ```

### 5. Test the Connection

Run your bot and try the `/register` command to ensure Supabase connectivity is working.

## 🔐 Security Configuration

### Row Level Security (RLS)

The schema includes a basic RLS policy. For production, you should implement stricter policies matched to your auth strategy.

### Environment Variables

- **SUPABASE_URL**: Your project URL (safe to expose to clients)
- **SUPABASE_ANON_KEY**: Public anon key (safe to expose to clients)

⚠️ **Never expose your service_role key in client-side code!**

## 📊 Database Structure

The `users` table includes:
- `user_id` (TEXT, PRIMARY KEY): Telegram user ID
- `telegram_username` (TEXT): Telegram username
- `first_name` (TEXT): Optional
- `last_name` (TEXT): Optional
- `created_at` (TIMESTAMP): Registration timestamp
- `last_active` (TIMESTAMP): Last activity timestamp
- `is_active` (BOOLEAN): Soft delete flag

## 🔧 Troubleshooting

### Common Issues

1. **Connection Error**: Verify your `SUPABASE_URL` and `SUPABASE_ANON_KEY`
2. **Permission Denied**: Check your RLS policies
3. **Table Not Found**: Ensure you've run the schema SQL

### Checking Data

You can view and manage data through the Supabase dashboard:
1. Go to **Table Editor**
2. Select the `users` table
3. View, edit, or delete records as needed

## 🚀 Production Considerations

1. **Backup**: Enable point-in-time recovery in your Supabase project
2. **Monitoring**: Set up database monitoring and alerts
3. **Scaling**: Supabase handles scaling automatically
4. **Security**: Review and tighten RLS policies for production

## 📈 Migration Notes

If you were previously using another storage, export your data and import it into Supabase via the dashboard or SQL.

---

For more detailed Supabase documentation, visit: https://supabase.com/docs
