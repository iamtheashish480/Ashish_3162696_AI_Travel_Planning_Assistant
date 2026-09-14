# Short Demonstration Guide

This is the recommended 3–5 minute demonstration for the assignment.

## 1. Start the application

```bash
streamlit run app.py
```

Explain that the UI is a Streamlit chat interface and that the LangChain agent can choose between the RAG tool and MCP tools.

## 2. Demonstrate RAG

Ask:

> Which neighbourhoods are suitable for cultural experiences in Singapore?

Show that the answer contains source-backed facts and source links. Explain that this request does not need a live MCP call.

## 3. Demonstrate MCP

Ask:

> What is the weather forecast for Singapore for the next three days?

Show the `### Real-Time Information (MCP)` section and point out that the forecast values include the retrieval time and Open-Meteo source returned by the MCP weather tool.

Then ask:

> Convert INR 50,000 to SGD.

Show that the conversion is live and comes from the MCP currency tool rather than a hard-coded rate.

## 4. Demonstrate the required combined scenario

Ask:

> Create a three-day Singapore itinerary for next week and adjust the activities according to the weather forecast.

Point out:

- RAG supplies destination attractions, itinerary ideas, transport and indoor/outdoor options.
- MCP supplies the future weather forecast.
- The final plan separates knowledge-base facts, current MCP information and generated recommendations.
- Weather-sensitive outdoor activities are changed when appropriate.

## 5. Demonstrate conversational context

First ask:

> Plan a three-day Singapore trip for my family.

Then ask:

> Make the second day more suitable for children.

Explain that the second turn is intentionally short and relies on `StreamlitChatMessageHistory` to retain the earlier family/three-day Singapore context.

## What to show in the final recording

A single screen recording should be enough. Keep it short and show:

1. the Streamlit interface;
2. one RAG-only response with citations;
3. one MCP weather response;
4. one MCP currency response;
5. the required combined weather-aware itinerary;
6. the two-turn context example.

The live values in weather and currency responses will vary. That is expected and is evidence that the tools are live rather than hard-coded.
