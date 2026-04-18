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
    st.query_params.clear()

# --- LOAD ASSETS ---
def get_base64_image(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

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

    /* Floating Action Button (FAB) */
    .custom-fab {{
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 60px;
        height: 60px;
        background: #00B386;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 1000000;
        cursor: pointer;
        text-decoration: none;
        transition: transform 0.2s ease;
    }}
    .custom-fab:hover {{ transform: scale(1.1); color: white; }}

    .pulse-effect {{
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: #00B386;
        opacity: 0.6;
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ transform: scale(1); opacity: 0.6; }}
        100% {{ transform: scale(1.6); opacity: 0; }}
    }}

    /* THE ULTIMATE SIDEBAR-AS-MODAL FIX (v3) */
    /* Detach sidebar from left and float in bottom-right */
    [data-testid="stSidebar"] {{
        position: fixed !important;
        right: 30px !important;
        left: auto !important;
        bottom: 105px !important;
        height: 600px !important;
        width: 400px !important;
        max-width: 90vw !important;
        background: #FFFFFF !important;
        border-radius: 24px !important;
        box-shadow: 0 12px 48px rgba(0,0,0,0.22) !important;
        z-index: 100000 !important;
        border: 1px solid #f0f0f0 !important;
        transition: all 0.3s cubic-bezier(0.165, 0.84, 0.44, 1) !important;
    }}

    /* Remove main content push/margin */
    [data-testid="stMain"] {{
        margin-left: 0 !important;
        padding-left: 0 !important;
    }}

    /* Hide the expansion/collapse controls */
    [data-testid="stSidebarCollapsedControl"] {{
        display: none !important;
    }}

    /* Hide sidebar standard header and styling */
    [data-testid="stSidebarNav"] {{
        display: none !important;
    }}

    /* Discovery Overlay */
    .discovery-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.45);
        z-index: 99999;
    }}

    .discovery-tooltip {{
        position: fixed;
        bottom: 110px;
        right: 30px;
        background: #fff;
        padding: 14px 20px;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        z-index: 1000001;
        font-size: 15px;
        font-weight: 600;
        color: #44475b;
    }}
    .discovery-tooltip:after {{
        content: '';
        position: absolute;
        bottom: -8px;
        right: 25px;
        border-width: 8px 8px 0;
        border-style: solid;
        border-color: #fff transparent transparent;
    }}

    /* Bottom Ribbon */
    .footer-ribbon {{
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: #111;
        color: #999;
        height: 32px;
        font-size: 11px;
        display: flex;
        align-items: center;
        padding: 0 20px;
        z-index: 10;
        border-top: 1px solid #222;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- MAIN APP LOGIC ---
def main():
    inject_custom_css()

    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False
    if "discovery_seen" not in st.session_state:
        st.session_state.discovery_seen = False
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- DISCOVERY ---
    if not st.session_state.discovery_seen and not st.session_state.chat_open:
        st.markdown('<div class="discovery-overlay"></div>', unsafe_allow_html=True)
        st.markdown('<div class="discovery-tooltip">Need help choosing funds? Chat with our AI assistant!</div>', unsafe_allow_html=True)

    # --- FAB ---
    fab_link = "/?open_chat=true" if not st.session_state.chat_open else "/?open_chat=false"
    st.markdown(f"""
    <a href="{fab_link}" class="custom-fab" target="_self">
        {"<div class='pulse-effect'></div>" if not st.session_state.chat_open else ""}
        <span style="font-size: 30px; z-index: 1000001;">{"🤖" if not st.session_state.chat_open else "✖️"}</span>
    </a>
    """, unsafe_allow_html=True)

    # --- CHAT MODAL (Relocated to Sidebar) ---
    if st.session_state.chat_open:
        with st.sidebar:
            # Header
            st.markdown("""
                <div style="padding: 10px 0 5px 0;">
                    <div style="font-weight:700; font-size:20px; color:#111; margin-bottom:2px;">MF FAQ Assistant</div>
                    <div style="font-size:13px; color:#777;">Groww AI • Facts & Data • v2.0</div>
                </div>
                <hr style="margin: 0 0 15px 0; border: 0; border-top: 1px solid #f0f0f0;">
            """, unsafe_allow_html=True)
            
            # History
            chat_box = st.container(height=400)
            with chat_box:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                        if msg.get("source"):
                            st.markdown(f'<small>[Source]({msg["source"]})</small>', unsafe_allow_html=True)

            # Input
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

            st.chat_input("Ask about Nippon Taiwan, ICICI Smallcap...", key="chat_input_val", on_submit=on_chat_submit)

    # --- MARQUEE ---
    st.markdown("""
    <div class="footer-ribbon">
        Currently answering for: ICICI Prudential ELSS • Bluechip • Smallcap • Midcap • Nippon India Taiwan
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
