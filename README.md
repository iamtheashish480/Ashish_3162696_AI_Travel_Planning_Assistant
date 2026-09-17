# Singapore Travel Planning Assistant

A small travel-planning application that combines a Singapore travel knowledge base with live information retrieved through the Model Context Protocol (MCP).

The project is deliberately focused on the assignment requirements rather than on a large UI. The main workflow is:

**Streamlit → LangChain agent → RAG knowledge base and/or MCP tools → grounded response**

## What the application demonstrates

- Singapore destination knowledge using Retrieval-Augmented Generation (RAG)
- Semantic retrieval with Hugging Face embeddings and FAISS
- Source title and URL metadata in retrieved documents
- Live weather forecasts through an MCP weather tool
- Live currency conversion through an MCP currency tool
- Combined RAG + MCP planning for weather-aware itineraries
- Multi-turn conversation context in the Streamlit session
- Explicit handling of missing knowledge and failed live services

## Architecture

```text
                         ┌─────────────────────┐
                         │    Streamlit UI     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    LangChain Agent  │
                         └───────┬─────┬───────┘
                                 │     │
                   ┌─────────────┘     └──────────────┐
                   ▼                                  ▼
          ┌──────────────────┐              ┌──────────────────┐
          │ RAG Knowledge    │              │ MCP Client       │
          │ Base             │              │ (stdio)          │
          └────────┬─────────┘              └────────┬─────────┘
                   │                                  │
                   ▼                                  ▼
          ┌──────────────────┐              ┌──────────────────┐
          │ FAISS + MiniLM   │              │ MCP Server       │
          │ Embeddings       │              │                  │
          └──────────────────┘              ├─ weather tool    │
                                            └─ currency tool   │
                                                     │
                                           ┌─────────┴─────────┐
                                           ▼                   ▼
                                      Open-Meteo        ExchangeRate-API
```

### Why the MCP layer is separate

The application does not call the weather or currency APIs directly from the LangChain tools. `mcp_server.py` exposes two tools using the official MCP Python SDK. `mcp_client.py` connects to that server through MCP's standard stdio transport and makes the returned tools available to the LangChain agent.

This keeps stable destination knowledge in RAG and current information behind the MCP boundary.

## Knowledge base

The project uses three public Singapore travel resources supplied for the assignment:

1. **Wikivoyage Singapore Travel Guide**  
   https://en.wikivoyage.org/wiki/Singapore
2. **Visit Singapore: Essential Visitor Information**  
   https://www.visitsingapore.com/travel-guide-tips/essential-information/
3. **Visit Singapore: Sample Itineraries**  
   https://www.visitsingapore.com/itineraries/

The corresponding text files are stored under `data/`. Their original titles and URLs are retained in `rag_engine.py` as metadata so retrieved answers can cite the source.

The assignment asks for at least three public resources. This project uses exactly three and does not claim additional sources that are not included in the repository.

## RAG workflow

1. Load the three text documents with `TextLoader`.
2. Add source title, source URL, and source filename metadata.
3. Split the documents into overlapping chunks with `RecursiveCharacterTextSplitter`.
4. Generate embeddings with `sentence-transformers/all-MiniLM-L6-v2` through LangChain's Hugging Face integration.
5. Store the embeddings in FAISS.
6. Perform semantic similarity search for each knowledge-base question.
7. Apply a relevance threshold so unrelated questions can return a clear missing-information response instead of forcing a weak match.
8. Pass the retrieved content and source metadata to the LangChain agent.
9. The agent uses only retrieved content for destination facts and cites the source title and URL.

The vector store is cached in the running process so the index is not rebuilt for every user message.

## MCP tools

The MCP server exposes two tools:

### `get_weather_forecast`

- Location: Singapore
- Returns 1–7 days of forecast data
- Supports a future `start_date`, which is used for future-trip planning
- Returns temperature, precipitation, precipitation probability, and a readable weather description
- Data source: Open-Meteo
- The response includes the retrieval time and source

### `convert_currency`

- Converts an amount between three-letter currency codes
- Returns the converted amount, exchange rate, retrieval time, and service source
- Data source: ExchangeRate-API

The application connects to these tools through the official MCP Python client over stdio. If the MCP server or external service fails, the failure is surfaced instead of being replaced with invented data.

## Prompt and context strategy

The system prompt tells the model to:

- use RAG for stable destination facts;
- use MCP for current weather and exchange rates;
- avoid unsupported destination claims;
- state when the knowledge base does not contain enough information;
- report MCP failures without inventing values;
- distinguish knowledge-base facts, live MCP information, and AI-generated recommendations;
- use the user's previous turns and preserve constraints such as family travel, budget, trip length, and preferences;
- translate phrases such as "next week" into actual dates using the current Singapore date supplied to the prompt.

The UI stores conversation messages with `StreamlitChatMessageHistory` and passes the previous messages to the agent on each turn.

## Response structure

For requests that need the relevant information, the assistant uses:

```text
### Knowledge Base Facts & Sources

### Real-Time Information (MCP)

### Personalized Recommendations
```

The sections are used when applicable. A simple destination question does not need a weather or currency tool, while a weather-aware itinerary can use both RAG and MCP.

## Git repo details and installation process

1. Clone the Repository

Open a terminal and clone the GitHub repository:

git clone https://github.com/iamtheashish480/Ashish_3162696_Data_Science_Assignment.git

Navigate to the project directory:

cd Ashish_3162696_Data_Science_Assignment

## Setup

### 1. Create a virtual environment

Python 3.11 is recommended.

Windows:

```bash
python -m venv .venv
.venv\\Scripts\\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

The first RAG run may download the embedding model from Hugging Face.

### 3. Configure Gemini

Copy `.env.example` to `.env` and add your Google Gemini API key:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
```

Do not commit `.env` to Git.

### 4. Run the application

```bash
streamlit run app.py
```

The MCP server is started automatically as a child process when the LangChain agent calls one of the MCP-backed tools. It does not need to be started manually for normal use.

## Optional MCP server check

The MCP server can also be inspected independently with the MCP development tooling if the `mcp` CLI is installed:

```bash
mcp dev mcp_server.py
```

The important point is that `mcp_server.py` is an actual MCP server, not just a pair of ordinary Python functions.

## Sample questions and expected demonstrations

### 1. RAG-only question

**Question**

> Which neighbourhoods are suitable for cultural experiences in Singapore?

**Expected behavior**

The agent calls `search_knowledge_base`, answers from the supplied travel documents, and includes source title/URL references. It should not call weather or currency tools because the question is not time-sensitive.

### 2. Weather MCP question

**Question**

> What is the weather forecast for Singapore for the next three days?

**Expected behavior**

The agent calls `get_weather_forecast`. The exact values change with time, so the response should label them as MCP Tool Information and show the retrieval time/source returned by the tool.

### 3. Currency MCP question

**Question**

> Convert INR 50,000 to SGD.

**Expected behavior**

The agent calls `convert_currency` and reports the live exchange rate returned by the MCP tool. It must not use a hard-coded exchange rate.

### 4. Required combined scenario

**Question**

> Create a three-day Singapore itinerary for next week and adjust the activities according to the weather forecast.

**Expected behavior**

The agent should:

1. retrieve attractions, itinerary ideas, transportation guidance, and indoor/outdoor information through RAG;
2. determine the three relevant future dates from the current Singapore date;
3. call the MCP weather tool for those dates;
4. produce a day-by-day itinerary;
5. replace weather-sensitive outdoor activities with appropriate indoor alternatives when the forecast makes that sensible;
6. distinguish RAG facts, MCP values, and generated recommendations.

### 5. Combined budget scenario

**Question**

> I have a budget of INR 60,000. Convert it to SGD and suggest a three-day Singapore itinerary.

**Expected behavior**

The agent should use RAG for the itinerary and the MCP currency tool for the current conversion. Any spending suggestions should be described as recommendations rather than presented as exact source facts unless the knowledge base supports them.

### 6. Multi-turn context scenario

**Turn 1**

> Plan a three-day Singapore trip for my family.

**Turn 2**

> Make the second day more suitable for children.

**Expected behavior**

The second request should use the retained conversation context instead of asking the user to repeat the three-day Singapore/family constraint.

### 7. Missing-knowledge scenario

**Question**

> What are the best ski resorts in Singapore?

**Expected behavior**

The RAG tool should be unable to provide sufficiently relevant ski-resort information and the assistant should say that the requested information is not available in the knowledge base rather than inventing a ski recommendation.

## Acceptance-criteria checklist

| Assignment criterion                         | Implementation                                                         |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| Knowledge base from at least three resources | Three public Singapore sources under `data/`                           |
| Embedding-based semantic retrieval           | Hugging Face MiniLM + FAISS                                            |
| Grounded answers with sources                | RAG metadata includes source title and URL; prompt requires citations  |
| Weather through MCP                          | `get_weather_forecast` on `mcp_server.py`                              |
| Currency through MCP                         | `convert_currency` on `mcp_server.py`                                  |
| At least one combined RAG + MCP response     | Required three-day weather-aware scenario                              |
| Multi-turn retained context                  | `StreamlitChatMessageHistory`                                          |
| Tool selection based on intent               | LangChain agent prompt + distinct tool descriptions                    |
| Missing knowledge/tool failures              | Relevance threshold + explicit MCP failure messages                    |
| Simple usable UI                             | Streamlit chat interface                                               |
| Prompt/context strategy documented           | This README and `agent.py`                                             |
| Sample questions/responses                   | Sample scenarios in this README and `sample.txt`                       |
| Short demonstration                          | The six test scenarios above cover RAG, MCP, combined use, and context |

## Project files

```text
.
├── app.py
├── agent.py
├── mcp_client.py
├── mcp_server.py
├── rag_engine.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── sample.txt
└── data/
    ├── wikivoyage_singapore.txt
    ├── visit_singapore_essential.txt
    └── visit_singapore_itineraries.txt
```

## Notes on live values and source reuse

Weather and exchange-rate results are time-sensitive. The values shown by the running application will change as external services update. The repository's static sample material therefore describes expected behavior rather than pretending that an old exchange rate or forecast is still current.

The included knowledge-base files retain the source titles and URLs supplied for this assignment. When redistributing extracted public-source content, review the applicable reuse terms of each source.
