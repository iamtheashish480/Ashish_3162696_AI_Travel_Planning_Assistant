"""Streamlit user interface for the Singapore Travel Planning Assistant."""

from __future__ import annotations

import streamlit as st
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

from agent import build_agent


st.set_page_config(
    page_title="Singapore Travel Planning Assistant",
    page_icon="✈️",
    layout="wide",
)

st.title("Singapore Travel Planning Assistant")
st.caption(
    "RAG-based destination knowledge + live MCP weather and currency tools"
)

with st.sidebar:
    st.subheader("What this app can do")
    st.markdown(
        """
- Answer Singapore destination questions from the project knowledge base
- Show source titles and links used by RAG
- Retrieve a live weather forecast through MCP
- Convert currencies through MCP
- Combine RAG and MCP for weather-aware trip planning
- Remember earlier turns in this chat session
        """
    )
    if st.button("Clear conversation"):
        st.session_state.pop("chat_messages", None)
        st.rerun()


@st.cache_resource(show_spinner=False)
def get_agent():
    return build_agent()


history = StreamlitChatMessageHistory(key="chat_messages")

for message in history.messages:
    role = "assistant" if message.type == "ai" else message.type
    st.chat_message(role).markdown(message.content)


user_input = st.chat_input(
    "Ask about Singapore, weather, currency, or a weather-aware itinerary..."
)

if user_input:
    st.chat_message("user").markdown(user_input)
    history.add_user_message(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Checking the knowledge base and live tools..."):
            try:
                response = get_agent().invoke({"messages": history.messages})
                output = response["messages"][-1].content
                if isinstance(output, list):
                    output = "".join(
                        block.get("text", "")
                        for block in output
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                output = str(output)
            except Exception as exc:
                output = (
                    "I could not complete that request because the application "
                    f"encountered an error: `{exc}`"
                )

            st.markdown(output)
            history.add_ai_message(output)
