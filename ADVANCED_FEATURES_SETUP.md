# 🚀 Advanced AI Features Setup Guide

This guide will help you set up the advanced AI features for MySecondMind, transforming it into a ChatGPT-level intelligent assistant.

## 🎯 What You'll Get

### ✨ **Advanced Natural Language Processing**
- ChatGPT-level conversation intelligence using Groq Llama-3.1 70B
- Context-aware responses that remember your conversation
- Multi-turn conversations with intelligent followups
- Smart content transformation and routing

### 🔍 **Semantic Search & Embeddings**
- True meaning-based search beyond keyword matching
- Content recommendations and clustering
- Fast vector similarity search with FAISS
- Local embeddings using sentence-transformers (100% free)

### ⏰ **Intelligent Notification System**
- Natural time parsing ("tomorrow at 3pm", "in 2 hours")
- Smart followups for incomplete requests
- Recurring reminders and tasks
- Actual notification delivery via Telegram

### 🧠 **Memory Resurfacing**
- Nightly summaries of your saved content (1-3 lines each)
- Random knowledge sharing for retention
- Morning briefings with weather and tasks
- Spaced repetition algorithm for important content

## 📋 Prerequisites

Before starting, make sure you have:
- ✅ Working MySecondMind bot (basic setup complete)
- ✅ Supabase database configured
- ✅ Render deployment working
- ✅ GROQ_API_KEY in environment variables

## 🛠️ Step 1: Install Dependencies

Update your requirements.txt (already done) and install:

```bash
pip install -r requirements.txt
```

**Key new dependencies:**
- `sentence-transformers>=3.0.0` - Local embeddings
- `faiss-cpu>=1.8.0` - Vector search
- `parsedatetime>=2.6` - Natural time parsing
- `APScheduler>=3.10.4` - Notification scheduling

## 🗄️ Step 2: Database Schema Updates

Apply the advanced database schema to your Supabase project:

### 2.1 Run Advanced Schema SQL
In Supabase SQL Editor, run the contents of `supabase_advanced_schema.sql`:

```sql
-- This creates tables for:
-- - conversation_history (AI context)
-- - notifications (scheduling)
-- - content_embeddings (semantic search)
-- - user_preferences (personalization)
-- - memory_resurface_log (knowledge retention)
-- - usage_analytics (insights)
```

### 2.2 Enable Vector Extension (if not already enabled)
```sql
CREATE EXTENSION IF NOT EXISTS "vector" CASCADE;
```

## 🔧 Step 3: Environment Variables

Add these to your Render environment variables:

### Required:
```
GROQ_API_KEY=your_groq_api_key_here
SUPABASE_SERVICE_ROLE=your_service_role_key_here
```

### Optional (but recommended):
```
WEATHER_API_KEY=your_weather_api_key_here
```

**Getting Weather API Key:**
1. Sign up at [OpenWeatherMap](https://openweathermap.org/api) (free tier available)
2. Get your API key
3. Add to environment variables

## 🚀 Step 4: Deploy Updated Code

1. **Push to GitHub:**
```bash
git add -A
git commit -m "Add advanced AI features"
git push origin main
```

2. **Redeploy on Render:**
   - Go to your Render dashboard
   - Click "Manual Deploy" or wait for auto-deploy
   - Check logs for successful initialization

## ✅ Step 5: Test Advanced Features

### 5.1 Test Advanced Conversations
Try these in Telegram:

```
"I learned something interesting about quantum computing today"
"Remind me to call mom tomorrow at 3pm"  
"What did I save about productivity?"
"I need to finish my project by Friday"
```

### 5.2 Test Semantic Search
Save some content, then try:
```
"Find content about artificial intelligence"
"Show me everything related to productivity"
```

### 5.3 Test Time Parsing
```
"Remind me in 2 hours to check email"
"Set a reminder for next Monday morning"
"Every day at 9am remind me to exercise"
```

## 🎛️ Step 6: User Preferences (Optional)

Users can customize their experience:

```sql
-- Update user preferences in Supabase
UPDATE user_preferences 
SET 
    morning_brief_time = '08:00',
    evening_summary_time = '20:00',
    memory_resurface_frequency = 'weekly',
    ai_personality = 'casual'
WHERE user_id = YOUR_USER_ID;
```

## 📊 Step 7: Monitor Performance

Check Render logs for:
- ✅ "Advanced AI conversation engine initialized"
- ✅ "Semantic search engine initialized"  
- ✅ "Notification scheduler initialized"
- 🔍 Semantic search queries working
- ⏰ Notifications being scheduled

## 🐛 Troubleshooting

### Issue: "Semantic search not available"
**Solution:** 
- Check if sentence-transformers installed correctly
- Verify sufficient memory on Render (upgrade plan if needed)

### Issue: "Advanced AI initialization failed"
**Solution:**
- Verify GROQ_API_KEY is set correctly
- Check Groq API quota/limits

### Issue: "Notification scheduler initialization failed"
**Solution:**
- Verify APScheduler is installed
- Check for port conflicts

### Issue: Embeddings taking too long
**Solution:**
- Consider upgrading Render plan for more CPU/memory
- Embeddings are generated on first use (one-time setup)

## 🎯 Step 8: Advanced Configuration

### 8.1 Customize AI Personality
Edit `core/advanced_ai.py` to change personality traits:
```python
personality_traits = {
    'helpful': "Professional and focused",
    'casual': "Friendly with emojis", 
    'professional': "Formal business style"
}
```

### 8.2 Adjust Semantic Search
Edit `core/semantic_search.py` to:
- Change embedding model (`all-MiniLM-L6-v2` vs `all-mpnet-base-v2`)
- Adjust similarity thresholds
- Customize clustering parameters

### 8.3 Configure Notifications
Edit `core/notification_scheduler.py` to:
- Change morning briefing time
- Adjust memory resurfacing frequency
- Customize notification messages

## 🎉 You're All Set!

Your MySecondMind bot now has:
- 🧠 ChatGPT-level intelligence
- 🔍 Semantic search capabilities
- ⏰ Smart notification system
- 🧩 Memory resurfacing features

## 💡 Usage Tips

1. **Start conversations naturally** - the AI understands context
2. **Use natural time expressions** - "tomorrow afternoon", "in 30 minutes"
3. **Ask follow-up questions** - the AI remembers your conversation
4. **Let it suggest actions** - it will proactively help you
5. **Trust the semantic search** - it finds content by meaning, not just keywords

## 🆘 Need Help?

If you encounter issues:
1. Check Render logs for error messages
2. Verify all environment variables are set
3. Ensure Supabase schema is applied correctly
4. Test with simple commands first
5. Check that dependencies installed successfully

Your bot is now a truly intelligent second brain! 🧠✨
