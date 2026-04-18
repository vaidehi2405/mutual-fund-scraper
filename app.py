import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import streamlit as st
import base64
import re
import html
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
    .stApp {{
        background-image: url("data:image/png;base64,{DASHBOARD_B64}");
        background-size: cover;
        background-position: top center;
        background-attachment: fixed;
    }}

    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    #MainMenu {{visibility: hidden;}}

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

    /* Chatbox modal shell */
    [data-testid="stSidebar"] {{
        position: fixed !important;
        right: 24px !important;
        left: auto !important;
        bottom: 56px !important;
        height: min(86vh, 740px) !important;
        width: min(92vw, 620px) !important;
        max-width: 620px !important;
        background: #EAF1EE !important;
        border-radius: 20px !important;
        box-shadow: 0 16px 42px rgba(16, 24, 40, 0.26) !important;
        z-index: 100001 !important;
        border: 1px solid #D8E4DF !important;
        transition: all 0.3s cubic-bezier(0.165, 0.84, 0.44, 1) !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        border-radius: 20px !important;
        overflow: hidden !important;
    }}
    [data-testid="stSidebarUserContent"] {{
        padding: 0 !important;
        background: #EAF1EE !important;
    }}

    [data-testid="stMain"] {{
        margin-left: 0 !important;
        padding-left: 0 !important;
    }}

    [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
    [data-testid="stSidebarNav"] {{ display: none !important; }}

    .modal-close-btn {{
        position: absolute;
        top: 16px;
        right: 16px;
        font-size: 20px;
        color: rgba(255,255,255,0.95);
        text-decoration: none;
        font-weight: 300;
        z-index: 100005;
        cursor: pointer;
        padding: 0 6px;
    }}
    .modal-close-btn:hover {{
        color: #ffffff;
        background: rgba(255,255,255,0.15);
        border-radius: 6px;
    }}

    .discovery-overlay {{
        position: fixed;
        inset: 0;
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

    .chat-shell {{
        display: flex;
        flex-direction: column;
        height: 100%;
    }}
    .chat-header-card {{
        background: linear-gradient(180deg, #10B58D 0%, #08A97F 100%);
        padding: 18px 22px;
        color: #fff;
        position: relative;
    }}
    .chat-title {{
        margin: 0;
        font-size: 40px;
        line-height: 1;
        font-weight: 700;
        letter-spacing: -0.02em;
    }}
    .chat-subtitle {{
        margin-top: 6px;
        font-size: 15px;
        opacity: 0.96;
        font-weight: 600;
    }}
    .advisory {{
        background: #DDF4ED;
        border-top: 1px solid #CDE7DE;
        border-bottom: 1px solid #CDE7DE;
        padding: 12px 18px;
        text-align: center;
        color: #146652;
        font-size: 16px;
        font-weight: 500;
        line-height: 1.3;
    }}
    .try-asking {{
        color: #8A8F94;
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin-bottom: 12px;
    }}
    .assistant-welcome {{
        background: #fff;
        border: 1px solid #D4DEDA;
        border-radius: 14px;
        padding: 12px 14px;
        color: #3F4650;
        font-size: 16px;
        line-height: 1.4;
        margin-bottom: 14px;
    }}
    .msg {{
        margin-bottom: 10px;
        padding: 12px 14px;
        border-radius: 14px;
        font-size: 15px;
        line-height: 1.45;
        color: #1F2937;
        border: 1px solid #D8E2DE;
        background: #fff;
    }}
    .msg.user {{
        margin-left: 40px;
        background: #D6F9EB;
        border-color: #AEEBCF;
    }}
    .msg.assistant {{
        margin-right: 24px;
    }}
    .source-link {{
        margin-top: 6px;
        display: block;
        font-size: 12px;
    }}
    [data-testid="stChatInput"] {{
        background: #F4F7F6;
        border-top: 1px solid #D7E2DD;
        padding: 14px 16px 18px 16px;
    }}
    [data-testid="stChatInput"] textarea {{
        background: #EBEFEE !important;
        border-radius: 999px !important;
        color: #3F4650 !important;
        font-size: 16px !important;
        border: 1px solid transparent !important;
    }}
    [data-testid="stChatInput"] button {{
        background: linear-gradient(180deg, #16C39A 0%, #00B386 100%) !important;
        color: white !important;
        border-radius: 999px !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        text-align: left;
        border: 1px solid #D4DFDB;
        background: #fff;
        color: #3F454E;
        border-radius: 14px;
        padding: 14px 16px;
        font-size: 16px;
        margin-bottom: 10px;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        border-color: #A9CEC2;
        color: #222;
    }}

    @media (max-width: 760px) {{
        [data-testid="stSidebar"] {{
            right: 0 !important;
            bottom: 0 !important;
            width: 100vw !important;
            max-width: 100vw !important;
            height: 100vh !important;
            border-radius: 0 !important;
        }}
        .chat-title {{ font-size: 30px; }}
        .advisory {{ font-size: 14px; }}
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
        quick_questions = [
            "What is the expense ratio of ICICI Bluechip Fund?",
            "What is the lock-in period for ELSS?",
            "Who is the fund manager for Small Cap fund?",
        ]

        def send_prompt(prompt: str):
            if not prompt:
                return
            st.session_state.messages.append({"role": "user", "content": prompt})
            response = run_pipeline(prompt)
            source_match = re.search(r"Source:\s*(https?://[^\s|]+)", response)
            source_url = source_match.group(1).strip() if source_match else None
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "source": source_url,
            })

        with st.sidebar:
            st.markdown('<a href="/?open_chat=false" class="modal-close-btn" target="_self">✕</a>', unsafe_allow_html=True)
            st.markdown('<div class="chat-shell">', unsafe_allow_html=True)
            st.markdown("""
                <div class="chat-header-card">
                    <div class="chat-title">MF FAQ Assistant</div>
                    <div class="chat-subtitle">Groww · Facts only · No investment advice</div>
                </div>
                <div class="advisory">Facts only. No investment advice. Always consult a SEBI-registered advisor.</div>
            """, unsafe_allow_html=True)

            chat_box = st.container(height=430)
            with chat_box:
                if not st.session_state.messages:
                    st.markdown('<div class="try-asking">TRY ASKING</div>', unsafe_allow_html=True)
                    for idx, question in enumerate(quick_questions):
                        if st.button(f"•  {question}", key=f"quick_q_{idx}", use_container_width=True, type="secondary"):
                            send_prompt(question)
                            st.rerun()
                else:
                    for msg in st.session_state.messages:
                        role_class = "user" if msg["role"] == "user" else "assistant"
                        content = html.escape(msg["content"])
                        st.markdown(f'<div class="msg {role_class}">{content}</div>', unsafe_allow_html=True)
                        if msg.get("source"):
                            source = html.escape(msg["source"])
                            st.markdown(f'<a class="source-link" href="{source}" target="_blank">Source</a>', unsafe_allow_html=True)

            def on_chat_submit():
                prompt = st.session_state.chat_input_val
                send_prompt(prompt)

            st.chat_input("Ask a factual question about MF schemes", key="chat_input_val", on_submit=on_chat_submit)
            st.markdown('</div>', unsafe_allow_html=True)

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
