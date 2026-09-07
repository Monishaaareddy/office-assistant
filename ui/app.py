"""
app.py — Person 4 (UI)
-----------------------
Streamlit chat interface for the TechNova Office Assistant, wired to
agent/agent.py's OfficeAssistant class.

Adds a persistent History sidebar (SQLite-backed) that survives
"Clear conversation" — history is only removed if you explicitly
delete it, never by clearing the current screen.

Run from the repo root:
    export GEMINI_API_KEY=your-key-here
    streamlit run ui/app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st

# Make the repo root importable regardless of where Streamlit is launched from
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# --- Persistent history (SQLite) --------------------------------------------
from memory.conversation_history import (  # noqa: E402
    initialize_database,
    save_chat,
    get_history,
    get_chat,
)

initialize_database()

st.set_page_config(page_title="NovaTrix Office Assistant", page_icon="🏢", layout="centered")

st.title("🏢 NovaTrix Office Assistant")
st.caption("Ask about company policies, or check your own leave balance, expenses, and IT assets.")

# --- API key check ----------------------------------------------------------
if not os.environ.get("GEMINI_API_KEY"):
    st.error(
        "GEMINI_API_KEY is not set. Set it in your terminal before running Streamlit, e.g.:\n\n"
        "```\nexport GEMINI_API_KEY=your-key-here\nstreamlit run ui/app.py\n```"
    )
    st.stop()

# --- Load the agent (once per browser session) ------------------------------
from agent.agent import OfficeAssistant  # noqa: E402

if "assistant" not in st.session_state:
    st.session_state.assistant = OfficeAssistant()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # current-screen chat only (resets on Clear)

if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

# --- Sidebar ------------------------------------------------------------------
with st.sidebar:

    # ---- Persistent history (survives Clear conversation) ----
    st.subheader("💬 History")

    history = get_history()

    if history:
        for history_id, question, answer, created_at in history:
            display_question = question.strip()
            if len(display_question) > 45:
                display_question = display_question[:45] + "..."

            if st.button(display_question, use_container_width=True, key=f"history_{history_id}"):
                selected_chat = get_chat(history_id)
                if selected_chat:
                    _, saved_question, saved_answer, _ = selected_chat
                    st.session_state.chat_history = [
                        ("user", saved_question),
                        ("assistant", saved_answer),
                    ]
                    st.session_state.assistant = OfficeAssistant()
                    st.session_state.pending_input = None
                    st.rerun()
    else:
        st.caption("No history yet.")

    st.divider()

    # ---- Example questions ----
    st.subheader("💡 Try asking")
    examples = [
        "What is the work from home policy?",
        "How many leaves does EMP004 have?",
        "Who is the manager of EMP001?",
        "What is the travel policy for hotel bookings?",
        "What IT assets does EMP004 have?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=f"example_{ex}"):
            st.session_state.pending_input = ex
            st.rerun()

    st.divider()

    # ---- Clear CURRENT screen only — does NOT touch saved history ----
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.assistant = OfficeAssistant()
        st.session_state.pending_input = None
        st.rerun()

# --- Render current-screen chat ----------------------------------------------
for role, text in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(text)

# --- Handle new input: typed, or from a sidebar example/history button ------
user_input = st.chat_input("Ask a question...")
if st.session_state.pending_input:
    user_input = st.session_state.pending_input
    st.session_state.pending_input = None

if user_input:
    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = st.session_state.assistant.answer(user_input)
            except Exception as e:
                answer = f"Sorry, something went wrong: {e}"
        st.markdown(answer)

    st.session_state.chat_history.append(("assistant", answer))

    # Save permanently — this is what survives "Clear conversation"
    save_chat(user_input, answer)