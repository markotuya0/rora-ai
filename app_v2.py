import streamlit as st
import requests
from datetime import datetime
import os

# API Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Rora AI - Text-to-SQL",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    
    # Health check
    try:
        health = requests.get(f"{API_URL}/health").json()
        st.success(f"✅ API: {health['status']}")
        st.info(f"Model: {health['model']}")
    except:
        st.error("❌ API offline")
    
    st.markdown("---")
    
    # History
    if st.button("🔄 Refresh History"):
        st.rerun()
    
    try:
        history_data = requests.get(f"{API_URL}/history?limit=5").json()
        st.subheader("📜 Recent Queries")
        for item in reversed(history_data['history']):
            with st.expander(f"Q: {item['question'][:30]}..."):
                st.code(item['sql_query'], language="sql")
                st.caption(item['timestamp'])
    except:
        st.warning("No history available")

# Main
st.title("🤖 Rora AI - Text-to-SQL Intelligence")
st.markdown("Transform natural language into SQL queries with AI")

# Check API connection
try:
    health = requests.get(f"{API_URL}/health", timeout=2).json()
    st.session_state['api_online'] = True
except:
    st.session_state['api_online'] = False
    st.error("⚠️ API is offline. Please start the API server: `python api.py`")

col1, col2 = st.columns([2, 1])

with col1:
    question = st.text_input(
        "Your Question:",
        placeholder="e.g., Who scored the highest in Math?",
        key="question_input"
    )

with col2:
    try:
        if st.session_state.get('api_online'):
            history_count = len(requests.get(f"{API_URL}/history", timeout=2).json().get('history', []))
            st.metric("Total Queries", history_count)
        else:
            st.metric("Total Queries", 0)
    except:
        st.metric("Total Queries", "N/A")

if st.button("🚀 Execute Query", type="primary"):
    if not question:
        st.warning("Please enter a question")
    else:
        with st.spinner("Generating SQL..."):
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": question}
                ).json()
                
                st.success("✅ Query executed successfully!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🧠 Generated SQL")
                    st.code(response['sql_query'], language="sql")
                
                with col2:
                    st.subheader("📈 Result")
                    st.text(response['result'])
                
                st.caption(f"Executed at: {response['timestamp']}")
                
            except requests.exceptions.RequestException as e:
                st.error(f"❌ API Error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Example queries
with st.expander("💡 Example Queries"):
    examples = [
        "Who scored the highest in Math?",
        "Show all students with grade A",
        "What is the average score in Science?",
        "List students who scored below 70"
    ]
    for ex in examples:
        st.code(ex)

st.markdown("---")
st.caption("🤖 Rora AI | Powered by FastAPI • LangChain • Ollama • Streamlit")
st.caption("Made with ❤️ by [Marko Tuya](https://github.com/markotuya0/rora-ai)")
