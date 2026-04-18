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
    /* Background Image - Fixed & High Fidelity */
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

    /* Floating Action Button (FAB) - Clean Version */
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
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 100000;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}
    .custom-fab:hover {{ transform: scale(1.1); }}

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

    /* THE ULTIMATE SIDEBAR-AS-MODAL FIX (v3) */
    [data-testid="stSidebar"] {{
        position: fixed !important;
        right: 30px !important;
        left: auto !important;
        bottom: 115px !important;
        height: 620px !important;
        width: 400px !important;
        max-width: 90vw !important;
        background: #FFFFFF !important;
        border-radius: 24px !important;
        box-shadow: 0 12px 48px rgba(0,0,0,0.22) !important;
        z-index: 100001 !important;
        border: 1px solid #f0f0f0 !important;
        transition: all 0.3s cubic-bezier(0.165, 0.84, 0.44, 1) !important;
    }}

    [data-testid="stMain"] {{
        margin-left: 0 !important;
        padding-left: 0 !important;
    }}

    [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
    [data-testid="stSidebarNav"] {{ display: none !important; }}

    /* Close Button inside Modal */
    .modal-close-btn {{
        position: absolute;
        top: 20px;
        right: 25px;
        font-size: 22px;
        color: #777;
        text-decoration: none;
        font-weight: 300;
        transition: color 0.2s;
        z-index: 100005;
        cursor: pointer;
    }}
    .modal-close-btn:hover {{ color: #111; }}

    /* Discovery Overlay */
    .discovery-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.4);
        z-index: 99999;
    }}

    .discovery-tooltip {{
        position: fixed;
        bottom: 120px;
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

    /* PREMIUM MARQUEE FOOTER */
    .footer-marquee-ribbon {{
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: #000;
        height: 40px;
        display: flex;
        align-items: center;
        overflow: hidden;
        z-index: 99998;
        border-top: 1px solid #1e2433;
    }}

    .marquee-label {{
        background: #000;
        color: #00B386;
        font-size: 11px;
        font-weight: 700;
        padding: 0 20px;
        height: 100%;
        display: flex;
        align-items: center;
        border-right: 1px solid #1e2433;
        white-space: nowrap;
        z-index: 2;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .marquee-content {{
        display: flex;
        white-space: nowrap;
        animation: marquee-scroll 40s linear infinite;
    }}

    .marquee-item {{
        font-size: 12px;
        color: #aaa;
        padding: 0 30px;
        display: flex;
        align-items: center;
    }}

    @keyframes marquee-scroll {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX(-50%); }}
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

    # --- FAB (Floating Action Button) ---
    if not st.session_state.chat_open:
        st.markdown(f"""
        <a href="/?open_chat=true" class="custom-fab" target="_self">
            <div class="pulse-effect"></div>
            <span style="font-size:32px;">🤖</span>
        </a>
        """, unsafe_allow_html=True)

    # --- CHAT MODAL (Relocated to Sidebar) ---
    if st.session_state.chat_open:
        with st.sidebar:
            # Dedicated Close Button
            st.markdown('<a href="/?open_chat=false" class="modal-close-btn" target="_self">✖</a>', unsafe_allow_html=True)
            
            # Header
            st.markdown("""
                <div style="padding: 10px 0 5px 0;">
                    <div style="font-weight:700; font-size:22px; color:#111; margin-bottom:2px;">MF FAQ Assistant</div>
                    <div style="font-size:14px; color:#00B386; font-weight:600;">Groww AI Assistant • v2.0</div>
                </div>
                <hr style="margin: 0 0 20px 0; border: 0; border-top: 1px solid #f0f0f0;">
            """, unsafe_allow_html=True)
            
            # History
            chat_box = st.container(height=420)
            with chat_box:
                if not st.session_state.messages:
                    with st.chat_message("assistant"):
                        st.write("Hello! I'm your Groww assistant. I have all the latest data on Mutual Funds. How can I help you today?")
                
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

            st.chat_input("Ask a question about funds…", key="chat_input_val", on_submit=on_chat_submit)

    # --- PREMIUM MARQUEE FOOTER ---
    fund_list = ["Nippon India Taiwan", "ICICI Prudential ELSS", "HDFC Mid Cap", "Parag Parikh Flexi Cap", "Bandhan Small Cap", "ICICI Prudential Bluechip", "ICICI Prudential Smallcap", "ICICI Prudential Midcap"]
    marquee_items = "".join([f'<div class="marquee-item">{fund}</div>' for fund in fund_list])
    
    st.markdown(f"""
    <div class="footer-marquee-ribbon">
        <div class="marquee-label">Answering For</div>
        <div class="marquee-content">
            {marquee_items} {marquee_items}
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
