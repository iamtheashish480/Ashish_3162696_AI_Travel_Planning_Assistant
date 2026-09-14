"""LangChain agent for the Singapore travel assistant."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from mcp_client import mcp_currency_converter, mcp_weather_forecast
from rag_engine import retrieve_knowledge


load_dotenv()


@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """Search the Singapore travel knowledge base for destination facts.

    Use this for attractions, neighbourhoods, transportation, culture,
    practical tips, food/local experiences, family activities, and itineraries.
    Do not use this tool as a source of current weather or exchange rates.
    """
    try:
        matches = retrieve_knowledge(query)
    except Exception as exc:
        return f"[RAG FAILURE] Knowledge base could not be searched: {exc}"

    if not matches:
        return (
            "[RAG NO SUFFICIENT MATCH]\n"
            "Information not available in knowledge base."
        )

    results: list[str] = []
    for index, (doc, score) in enumerate(matches, start=1):
        title = doc.metadata.get("source_title", "Unknown source")
        url = doc.metadata.get("source_url", "")
        results.append(
            f"Result {index}\n"
            f"Source Title: {title}\n"
            f"Source Link: {url}\n"
            f"Relevance Score: {score:.2f}\n"
            f"Content:\n{doc.page_content}"
        )

    return "\n\n---\n\n".join(results)


def build_agent():
    """Create the LangChain agent and expose RAG plus MCP-backed tools."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    today = datetime.now(ZoneInfo("Asia/Singapore")).date().isoformat()

    system_prompt = f"""
You are a Singapore travel planning assistant.

Current Singapore date: {today}.

The application has three types of information:
1. Knowledge-base facts from the Singapore travel documents.
2. Current information returned by MCP tools.
3. Recommendations you generate from the available facts and the user's preferences.

RULES

1. KNOWLEDGE-BASE FACTS
- Use search_knowledge_base for destination facts such as attractions,
  neighbourhoods, transportation, culture, practical tips, food/local
  experiences, family activities, and sample itineraries.
- Do not invent destination facts.
- If the RAG tool says "Information not available in knowledge base", say so
  clearly rather than filling the gap with unsupported destination facts.
- Cite the source title and URL for factual claims taken from RAG.

2. CURRENT INFORMATION / MCP
- Use get_weather_forecast for weather or forecast questions and for itinerary
  requests whose activities need to be adjusted to expected weather.
- Use convert_currency for currency conversion or budget requests involving
  exchange rates.
- Do not use a made-up exchange rate or weather value.
- If an MCP call fails, clearly state that the live external service was
  unavailable and do not fabricate a replacement value.
- Clearly label live tool information as "MCP Tool Information".

3. TOOL SELECTION
- Do not call weather or currency tools for ordinary destination questions
  that do not need current information.
- For a combined request, call both RAG and the relevant MCP tools.
- Preserve user preferences and constraints from earlier turns.

4. FUTURE TRIPS
- When the user says "next week" or gives future dates, determine the actual
  dates from the current Singapore date above and pass those dates to the
  weather MCP tool.
- For a three-day trip, obtain three days of weather when the request depends
  on weather.

5. RESPONSE STRUCTURE
Use these headings when applicable:
### Knowledge Base Facts & Sources
### Real-Time Information (MCP)
### Personalized Recommendations

Within recommendations, distinguish clearly between source-backed facts and
AI-generated planning suggestions. Keep recommendations practical and explain
weather-driven substitutions when relevant.

6. SOURCE DISCIPLINE
- Do not cite a source that was not returned by the knowledge-base tool.
- Do not present MCP values as knowledge-base facts.
- Do not present your own recommendations as source quotations.
"""

    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        google_api_key=api_key,
    )

    return create_agent(
        model=llm,
        tools=[
            search_knowledge_base,
            mcp_weather_forecast,
            mcp_currency_converter,
        ],
        system_prompt=system_prompt,
    )
