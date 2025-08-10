import logging
logging.basicConfig(
    filename='mcp_tool.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)


import asyncio
from typing import Annotated
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field

import markdownify
import httpx
import readabilipy
import json

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

# --- Fetch Utility Class ---
class Fetch:
    USER_AGENT = "Puch/1.0 (Autonomous)"

    @classmethod
    async def fetch_url(cls, url: str, user_agent: str, force_raw: bool = False) -> tuple[str, str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, follow_redirects=True, headers={"User-Agent": user_agent}, timeout=30)
            except httpx.HTTPError as e:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"))

            if response.status_code >= 400:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url} - status code {response.status_code}"))

            page_raw = response.text

        content_type = response.headers.get("content-type", "")
        is_page_html = "text/html" in content_type

        if is_page_html and not force_raw:
            return cls.extract_content_from_html(page_raw), ""
        return (page_raw, f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n")

    @staticmethod
    def extract_content_from_html(html: str) -> str:
        ret = readabilipy.simple_json.simple_json_from_html_string(html, use_readability=True)
        if not ret or not ret.get("content"):
            return "<error>Page failed to be simplified from HTML</error>"
        return markdownify.markdownify(ret["content"], heading_style=markdownify.ATX)

    @staticmethod
    async def google_search_links(query: str, num_results: int = 5) -> list[str]:
        ddg_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        links = []
        async with httpx.AsyncClient() as client:
            resp = await client.get(ddg_url, headers={"User-Agent": Fetch.USER_AGENT})
            if resp.status_code != 200:
                return ["<error>Failed to perform search.</error>"]

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", class_="result__a", href=True):
            href = a["href"]
            if "http" in href:
                links.append(href)
            if len(links) >= num_results:
                break
        return links or ["<error>No results found.</error>"]

# --- MCP Server Setup ---
mcp = FastMCP("Job Finder MCP Server", auth=SimpleBearerAuthProvider(TOKEN))

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
                        {"role": "system", "content": "You are a tech explainer. For any input, output four sections:\n1. 📖 Plain English:\n2. 🔹 TL;DR:\n3. 🍼 ELI5:\n4. 📊 Visual (text diagram)."},
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
        return [TextContent(type="text", text=explanation)]


        return [TextContent(type="text", text=explanation)]

    except Exception as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# --- Run MCP Server ---
async def main():
    print("🚀 Starting MCP server on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())
