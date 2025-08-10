import logging
import asyncio
from typing import Annotated
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, INTERNAL_ERROR
from pydantic import BaseModel, Field
import markdownify
import httpx
import readabilipy
import json
import re

# --- Setup logging ---
logging.basicConfig(
    filename='mcp_tool.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# --- Load environment variables ---
load_dotenv()
TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

assert TOKEN, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER, "Please set MY_NUMBER in your .env file"
assert OPENROUTER_API_KEY, "Please set OPENROUTER_API_KEY in your .env file"

# --- Auth Provider ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
        return None

# --- Rich Tool Description model ---
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# --- MCP Server Setup ---
mcp = FastMCP("Tech Translator MCP Server", auth=SimpleBearerAuthProvider(TOKEN))

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    return MY_NUMBER

# --- Tool: tech_translator with OpenRouter ---
TECH_TRANSLATOR_DESCRIPTION = RichToolDescription(
    description="Explains any technical or non-technical term in multiple ways: plain English, TL;DR, ELI5, and a diagram.",
    use_when="Use this when the user provides any term, phrase, or sentence they want explained clearly.",
)

@mcp.tool(description=TECH_TRANSLATOR_DESCRIPTION.model_dump_json())
async def tech_translator(
    tech_text: Annotated[str, Field(description="Any term, phrase, or sentence to explain")]
) -> list[TextContent]:
    try:
        logging.info(f"tech_translator input: {tech_text}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": "openai/gpt-oss-20b:free",
                    "messages": [
                        {"role": "system", "content": (
                            "You are a tech explainer. For any input, output four sections:\n"
                            "1. 📖 Plain English:\n"
                            "2. 🔹 TL;DR:\n"
                            "3. 🍼 ELI5:\n"
                            "4. 📊 Visual (text diagram)."
                        )},
                        {"role": "user", "content": tech_text}
                    ],
                    "temperature": 0.7
                })
            )

        if response.status_code != 200:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"OpenRouter API error: {response.text}"))

        api_data = response.json()
        explanation = api_data["choices"][0]["message"]["content"]

        logging.info(f"tech_translator output: {explanation}")

        # Split explanation into sections by numbers followed by a dot and whitespace
        parts = re.split(r'\n?\d+\.\s+', explanation)
        if parts and parts[0].strip() == "":
            parts = parts[1:]  # Remove empty first split if present

        titles = ["📖 Plain English:", "🔹 TL;DR:", "🍼 ELI5:", "📊 Visual (text diagram):"]
        texts = []

        for i, part in enumerate(parts):
            text = part.strip()
            if text:
                content = f"{titles[i]}\n{text}"
                texts.append(TextContent(type="text", text=content))

        return texts

    except Exception as e:
        logging.error(f"tech_translator error: {e}", exc_info=True)
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# --- Run MCP Server ---
async def main():
    print("🚀 Starting MCP server on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())
