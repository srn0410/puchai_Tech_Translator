# 🚀 Tech-Translator MCP Server for Puch AI
Tech-Translator is an AI-powered MCP tool designed to bridge the gap between tech experts and non-tech users. It transforms complex technical language into simple, easy-to-understand explanations — perfect for anyone struggling with jargon.

## ✨ Features
Multi-format explanations:
Plain English, TL;DR, ELI5 (explain like I’m 5), plus a text-based visual diagram

Context-aware AI: Understands complex tech phrases, code snippets, or documentation

Ideal users: Product Managers, HR, Non-tech founders, Elderly users, and more

Secure & easy to integrate: Uses token-based auth to keep your server safe

Powered by OpenRouter AI: Access cutting-edge LLMs for reliable, high-quality responses

## 🔥 Why Tech-Translator?
Never get lost in tech talk again!

Empowers teams to communicate clearly and efficiently

Helps non-tech stakeholders make better decisions

Bridges real-world communication gaps between technical and non-technical roles

## 🚀 Quick Setup Guide
Step 1: Install Dependencies
Make sure you have Python 3.11+ installed, then:

```python
# Create virtual environment
uv venv

# Install dependencies
uv sync

# Activate environment
source .venv/bin/activate
```

Step 2: Configure Environment Variables
Copy .env.example to .env and fill in your keys:
```env
AUTH_TOKEN=your_secret_token_here
MY_NUMBER=919876543210
OPENROUTER_API_KEY=your_openrouter_api_key_here
```
AUTH_TOKEN: Your secret token for securing API access

MY_NUMBER: Your WhatsApp number in international format

OPENROUTER_API_KEY: Key to access OpenRouter AI models (including free ones)

Step 3: Run the MCP Server
```bash
python mcp_tech_translator.py
```
Look for:
```chsarp
🚀 Starting MCP server on http://0.0.0.0:8086
```

Step 4: Expose Your Server Publicly
Use ngrok or deploy to a cloud platform so Puch AI can access your server over HTTPS.
```bash
ngrok http 8086
```
(You will need to install ngrok and provide the auth token)

### 🔗 Connect to Puch AI
1. Open Puch AI on WhatsApp

2. Start a new chat

3. Connect your MCP server:
   ```arduino
   /mcp connect https://your-ngrok-url.ngrok.app/mcp your_secret_token_here
   ```
## How to Use the Tech-Translator Tool via WhatsApp
Enter the command :
```bash
Run the MCP tool: tech_translator
Parameters:
tech_text = "The technical term, phrase, or sentence you want explained"
```
Fill the tech_text field with whatever you would like to ask Tech Translator
