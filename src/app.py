"""
Streamlit Entry Point — Groww × HDFC RAG FAQ Chatbot
UI: Groww brand colors (#00D09C green, #1B1F3B dark navy, #FFFFFF text)
Welcome screen + 3 example questions + facts-only disclaimer.
Run: streamlit run src/app.py
"""

import streamlit as st
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrieval.retriever import RAGRetriever

# Initialize the retriever only once
@st.cache_resource
def get_retriever():
    return RAGRetriever()

def main():
    # Configure page
    st.set_page_config(
        page_title="Groww - HDFC Mutual Fund Assistant",
        page_icon="📈",
        layout="centered"
    )

    # Custom CSS for Groww branding
    st.markdown("""
        <style>
        .stApp {
            background-color: #1B1F3B;
            color: #FFFFFF;
        }
        .stChatMessage {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 10px;
        }
        .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
            background-color: rgba(0, 208, 156, 0.1);
            border: 1px solid #00D09C;
        }
        h1, h2, h3 {
            color: #00D09C !important;
        }
        .disclaimer {
            font-size: 0.8rem;
            color: #A0A0A0;
            margin-bottom: 20px;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("HDFC Mutual Fund FAQ Assistant")
    st.markdown("<p class='disclaimer'>Facts-only assistant. No financial advice provided.</p>", unsafe_allow_html=True)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
        # Add a welcome message
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Hi! I can answer factual questions about 5 specific HDFC Mutual Funds available on Groww. How can I help you today?"
        })

    # Example questions in sidebar
    with st.sidebar:
        st.markdown("### Example Questions")
        st.markdown("- What is the expense ratio of HDFC Large Cap Fund?")
        st.markdown("- What is the exit load for HDFC Small Cap Fund?")
        st.markdown("- Minimum SIP for HDFC Flexi Cap?")
        st.markdown("---")
        st.markdown("### Supported Funds")
        st.markdown("- HDFC Large Cap Fund")
        st.markdown("- HDFC Flexi Cap Fund")
        st.markdown("- HDFC ELSS Tax Saver")
        st.markdown("- HDFC Small Cap Fund")
        st.markdown("- HDFC Balanced Advantage")

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Ask a question about an HDFC Mutual Fund..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            with st.spinner("Searching knowledge base..."):
                try:
                    retriever = get_retriever()
                    result = retriever.process_query(prompt)
                    response = result.answer
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Sorry, an error occurred: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()
