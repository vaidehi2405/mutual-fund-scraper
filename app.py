import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import streamlit as st
import base64
import re
from datetime import datetime, timezone
from app.pipeline import run_pipeline, get_collection
from app.refusal import DISCLAIMER

# --- SET PAGE CONFIG ---
st.set_page_config(
    page_title="MF FAQ Assistant | Groww",
    page_icon="https://groww.in/favicon.ico",
    layout="wide"
)

# Handle Query Params for FAB click
if "open_chat" in st.query_params:
    st.session_state.chat_open = (st.query_params["open_chat"] == "true")
    st.session_state.discovery_seen = True
    # Clear param to avoid sticky state
    st.query_params.clear()

# --- LOAD ASSETS ---
def get_base64_image(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Use the dashbaord image we prepared
DASHBOARD_B64 = get_base64_image("groww-chat-ui/src/assets/dashboard.png")

# --- CUSTOM CSS ---
def inject_custom_css():
    st.markdown(f"""
    <style>
    /* Background Image */
    .stApp {{
        background-image: url("data:image/png;base64,{DASHBOARD_B64}");
        background-size: cover;
        background-position: top center;
        background-attachment: fixed;
    }}

    /* Hide Streamlit Header & Footer */
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    #MainMenu {{visibility: hidden;}}

    /* Floating Action Button (FAB) - ROBUST HTML VERSION */
    .custom-fab {{
        position: fixed;
        bottom: 40px;
        right: 30px;
        width: 65px;
        height: 65px;
        background: #00B386;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 100000;
        cursor: pointer;
        text-decoration: none;
        transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}

    .custom-fab:hover {{
        transform: scale(1.1);
        color: white;
    }}

    .pulse-effect {{
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: #00B386;
        opacity: 0.6;
        animation: pulse 2s infinite;
        z-index: -1;
    }}

    @keyframes pulse {{
        0% {{ transform: scale(1); opacity: 0.6; }}
        100% {{ transform: scale(1.6); opacity: 0; }}
    }}

    /* Discovery Tooltip */
    .discovery-tooltip {{
        position: fixed;
        bottom: 115px;
        right: 30px;
        background: white;
        color: #44475b;
        padding: 14px 18px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        z-index: 100001;
        max-width: 260px;
        animation: slideIn 0.3s ease-out;
    }}

    .discovery-tooltip:after {{
        content: '';
        position: absolute;
        bottom: -8px;
        right: 24px;
        border-width: 8px 8px 0;
        border-style: solid;
        border-color: white transparent transparent;
    }}

    @keyframes slideIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Overlay - NO BLUR TO PREVENT TRAP */
    .discovery-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.45);
        z-index: 99999;
    }}

    /* Bottom Ribbon Marquee */
    .footer-ribbon {{
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: #0a0a0a;
        height: 32px;
        border-top: 0.5px solid #1e2433;
        display: flex;
        align-items: center;
        overflow: hidden;
        z-index: 99998;
    }}

    .ribbon-label {{
        background: #0a0a0a;
        color: #00B386;
        font-size: 10px;
        font-weight: 600;
        padding: 0 14px;
        height: 100%;
        display: flex;
        align-items: center;
        border-right: 0.5px solid #1e2433;
        white-space: nowrap;
        z-index: 2;
    }}

    .marquee-container {{
        display: flex;
        white-space: nowrap;
        animation: marquee 28s linear infinite;
    }}

    .marquee-item {{
        font-size: 11px;
        color: #bbb;
        padding: 0 20px;
        display: flex;
        align-items: center;
    }}

    .divider {{
        width: 1px;
        height: 12px;
        background: #1e2433;
    }}

    @keyframes marquee {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(-50%); }}
    }}
    </style>
    """, unsafe_allow_html=True)

# --- MAIN APP LOGIC ---
def main():
    inject_custom_css()

    # Initialize Session State
    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False
    if "discovery_seen" not in st.session_state:
        st.session_state.discovery_seen = False
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- DISCOVERY EXPERIENCE ---
    show_discovery = not st.session_state.discovery_seen and not st.session_state.chat_open
    if show_discovery:
        st.markdown('<div class="discovery-overlay"></div>', unsafe_allow_html=True)
        st.markdown('<div class="discovery-tooltip">Need help choosing funds? Chat with our AI assistant!</div>', unsafe_allow_html=True)

    # --- FLOATING ASSISTANT (FAB) ---
    # Using a robust HTML anchor that reloads with a query param
    st.markdown(f"""
    <a href="/?open_chat=true" class="custom-fab" target="_self">
        <div class="pulse-effect"></div>
        <span style="font-size: 32px;">🤖</span>
    </a>
    """, unsafe_allow_html=True)

    # --- CHAT OVERLAY ---
    if st.session_state.chat_open:
        with st.sidebar:
            st.image("https://groww.in/favicon.ico", width=30)
            st.title("MF FAQ Assistant")
            st.caption("Groww • Facts only • No advice")
            st.divider()

            # Display Messages
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    if msg.get("source"):
                        st.markdown(f'<small>[Source]({msg["source"]})</small>', unsafe_allow_html=True)

            # Chat Input
            def on_chat_submit():
                prompt = st.session_state.chat_input_val
                if prompt:
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    response = run_pipeline(prompt)
                    source_match = re.search(r"Source:\s*(https?://[^\s|]+)", response)
                    source_url = source_match.group(1).strip() if source_match else None
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response,
                        "source": source_url
                    })

            st.chat_input("Ask a factual question…", key="chat_input_val", on_submit=on_chat_submit)
            
            if st.button("Close Chat", type="secondary", use_container_width=True):
                st.session_state.chat_open = False
                st.rerun()

    # --- BOTTOM MARQUEE ---
    schemes = [
        "ICICI Prudential ELSS Tax Saver Fund",
        "ICICI Prudential Flexicap Fund",
        "ICICI Prudential Bluechip Fund",
        "ICICI Prudential Smallcap Fund",
        "ICICI Prudential Midcap Fund"
    ]
    marquee_content = "".join([f'<div class="marquee-item">{s}</div><div class="divider"></div>' for s in schemes])
    marquee_html = f'<div class="marquee-container">{marquee_content}{marquee_content}</div>'

    st.markdown(f"""
    <div class="footer-ribbon">
        <div class="ribbon-label">This chatbot works for</div>
        {marquee_html}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
