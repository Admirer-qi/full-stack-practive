# AI Integration for Todo List App

This application now includes AI capabilities powered by DeepSeek's API.

## Setup Instructions

### 1. Get a DeepSeek API Key
- Visit [DeepSeek Platform](https://platform.deepseek.com/)
- Sign up for an account if you don't have one
- Create an API key from the dashboard
- The free tier provides generous limits for testing

### 2. Configure the API Key

#### Option A: Environment Variable (Recommended)
```bash
# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="your_api_key_here"

# Windows (Command Prompt)
set DEEPSEEK_API_KEY=your_api_key_here

# Linux/Mac
export DEEPSEEK_API_KEY=your_api_key_here
```

#### Option B: Create a .env file
Copy `.env.example` to `.env` and replace `your_api_key_here` with your actual API key.

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

The application will start on `http://localhost:5000`

## Features

### AI Assistant Tab
- **Chat Interface**: Send messages to the AI assistant
- **Real-time Responses**: Get immediate answers from DeepSeek's model
- **Chat History**: View your conversation history
- **Auto-scroll**: Automatically scroll to new messages
- **Clear Chat**: Reset the conversation when needed

### Todo List Integration
The AI can help you with:
- Planning and organizing tasks
- Setting priorities
- Breaking down complex tasks
- Time management advice
- Productivity tips

## API Configuration

The AI functionality uses the following configuration in `app.py`:
- **API Endpoint**: `https://api.deepseek.com/v1/chat/completions`
- **Model**: `deepseek-chat`
- **System Prompt**: "You are a helpful assistant. Please provide clear and concise responses."

## API Key Format

### Important Note About API Key Format
DeepSeek API keys **do NOT** typically start with `sk-`. If your key starts with `sk-`, it's likely an OpenAI-style key that won't work with DeepSeek.

**Correct DeepSeek API key format:**
- Usually 32-64 characters long
- Does NOT start with `sk-`
- May contain letters, numbers, and hyphens
- Example: `dsk-abcdef1234567890...` or similar format

**How to get a valid DeepSeek API key:**
1. Go to [DeepSeek Platform](https://platform.deepseek.com/)
2. Sign in or create an account
3. Navigate to the API section
4. Generate a new API key
5. Copy the key (it will NOT start with `sk-`)

### Checking Your API Key
The application includes diagnostic tools to check your API key:
1. **Status check**: Visit `http://localhost:5000/api/ai/status`
2. **Connection test**: Visit `http://localhost:5000/api/ai/test`
3. **Web interface**: The AI Assistant tab shows key status and format info

## Troubleshooting

### Common Issues

1. **"DeepSeek API key not configured" error**
   - Make sure you've set the `DEEPSEEK_API_KEY` environment variable
   - Restart the Flask application after setting the variable

2. **"API request failed" error**
   - Check your internet connection
   - Verify your API key is valid and has not expired
   - Ensure you have sufficient credits in your DeepSeek account

3. **Slow responses**
   - The API might be experiencing high load
   - Check the DeepSeek status page for service updates

### Testing the API
You can test your API key with curl:
```bash
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

## Security Notes
- Never commit your `.env` file to version control
- Keep your API keys secret and secure
- Use environment variables in production deployments
- Consider rate limiting for production use

## Limitations
- Requires an active internet connection
- Subject to DeepSeek API rate limits and terms of service
- Responses may vary based on the model's training data
- Free tier has usage limits