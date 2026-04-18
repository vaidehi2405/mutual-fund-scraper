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

    /* FIXED WIDTH & FULL HEIGHT DRAWER (v5) */
    [data-testid="stSidebar"] {{
        position: fixed !important;
        right: 0px !important;
        left: auto !important;
        bottom: 0px !important;
        height: 100vh !important;
        width: 380px !important;
        max-width: 90vw !important;
        background: #EAF1EE !important;
        border-radius: 0 !important;
        box-shadow: -8px 0 32px rgba(16, 24, 40, 0.15) !important;
        z-index: 100001 !important;
        border-left: 1px solid #D8E4DF !important;
        transition: all 0.3s ease !important;
    }}
    
    /* Internal Flex Layout */
    [data-testid="stSidebarUserContent"] {{
        padding: 0 !important;
        height: 100vh !important;
        display: flex !important;
        flex-direction: column !important;
        background: #EAF1EE !important;
    }}

    [data-testid="stMain"] {{ margin-left: 0 !important; padding-left: 0 !important; }}
    [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
    [data-testid="stSidebarNav"] {{ display: none !important; }}

    .modal-close-btn {{
        position: absolute;
        top: 12px;
        right: 16px;
        font-size: 20px;
        color: rgba(255,255,255,0.95);
        text-decoration: none;
        z-index: 100005;
        cursor: pointer;
        padding: 4px;
    }}
    .modal-close-btn:hover {{
        background: rgba(255,255,255,0.15);
        border-radius: 50%;
    }}

    .chat-shell {{
        display: flex;
        flex-direction: column;
        flex: 1;
        height: 100%;
        overflow: hidden;
    }}
    
    /* Header (Auto Height) */
    .chat-header-card {{
        flex: 0 0 auto;
        background: linear-gradient(180deg, #10B58D 0%, #08A97F 100%);
        padding: 12px 16px; /* Compact py-3 px-4 */
        color: #fff;
        position: relative;
    }}
    .chat-title {{
        margin: 0;
        font-size: 20px; /* Reduced from 40px */
        font-weight: 700;
    }}
    .chat-subtitle {{
        margin-top: 2px;
        font-size: 13px;
        opacity: 0.9;
    }}
    
    .advisory {{
        flex: 0 0 auto;
        background: #DDF4ED;
        padding: 8px 16px;
        text-align: center;
        color: #146652;
        font-size: 12px;
        border-bottom: 1px solid #CDE7DE;
    }}

    /* History (Expandable) */
    .st-emotion-cache-12w0qpk {{ flex: 1 !important; }} /* Target the history container */
    
    .msg {{
        margin-bottom: 12px; /* gap-3 */
        padding: 12px 16px;
        border-radius: 12px;
        font-size: 14px;
        line-height: 1.45;
        max-width: 75% !important; /* Constrained message width */
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }}
    .msg.user {{
        background: #D6F9EB;
        border: 1px solid #AEEBCF;
        align-self: flex-end;
        margin-left: auto;
    }}
    .msg.assistant {{
        background: #fff;
        border: 1px solid #D8E2DE;
        align-self: flex-start;
        margin-right: auto;
    }}
    
    /* Suggestions Area */
    .suggestions-container {{
        flex: 0 0 auto;
        padding: 10px 16px;
        background: #EAF1EE;
    }}
    .try-asking {{
        color: #8A8F94;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }}
    /* Force horizontal scroll for suggestion buttons */
    .st-emotion-cache-1p732y4 {{ 
        display: flex !important; 
        overflow-x: auto !important; 
        flex-wrap: nowrap !important; 
        gap: 10px !important; 
        padding-bottom: 8px !important;
        scrollbar-width: none;
    }}
    .st-emotion-cache-1p732y4::-webkit-scrollbar {{ display: none; }}
    .st-emotion-cache-1p732y4 > div {{ flex: 0 0 auto !important; width: auto !important; }}

    /* Input (Fixed Bottom) */
    [data-testid="stChatInput"] {{
        flex: 0 0 auto;
        background: #F4F7F6;
        border-top: 1px solid #D7E2DD;
        padding: 12px 16px 12px 16px !important;
    }}
    [data-testid="stChatInput"] > div {{
        height: 44px !important; /* Target height */
    }}

    /* Global Proportions */
    .discovery-overlay {{ position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); z-index: 99999; }}
    .discovery-tooltip {{ position: fixed; bottom: 120px; right: 30px; background: #fff; padding: 14px 20px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.2); z-index: 1000001; font-size: 15px; font-weight: 600; color: #44475b; }}
    
    .footer-marquee-ribbon {{ position: fixed; bottom: 0; left: 0; width: 100%; background: #000; height: 40px; display: flex; align-items: center; overflow: hidden; z-index: 99998; border-top: 1px solid #1e2433; }}
    .marquee-label {{ background: #000; color: #00B386; font-size: 11px; font-weight: 700; padding: 0 20px; height: 100%; display: flex; align-items: center; border-right: 1px solid #1e2433; white-space: nowrap; text-transform: uppercase; letter-spacing: 0.5px; }}
    .marquee-content {{ display: flex; white-space: nowrap; animation: marquee-scroll 40s linear infinite; }}
    .marquee-item {{ font-size: 12px; color: #aaa; padding: 0 30px; display: flex; align-items: center; }}
    @keyframes marquee-scroll {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}
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
            "What is the expense ratio are there?",
            "What is the lock-in period for ELSS?",
            "Who is the fund manager?",
            "Nippon Taiwan Equity Fund?",
        ]

        def send_prompt(prompt: str):
            if not prompt: return
            st.session_state.messages.append({"role": "user", "content": prompt})
            response = run_pipeline(prompt)
            source_match = re.search(r"Source:\s*(https?://[^\s|]+)", response)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "source": source_match.group(1).strip() if source_match else None,
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

            history_box = st.container(height=0) # We will force its height via CSS to be flex-1
            with history_box:
                # Custom padding wrapper
                st.markdown('<div style="padding: 12px 16px; display: flex; flex-direction: column;">', unsafe_allow_html=True)
                if not st.session_state.messages:
                    st.markdown('<div class="msg assistant">Hi! I can help with mutual fund info like NAV, expense ratio, and returns.</div>', unsafe_allow_html=True)
                else:
                    for msg in st.session_state.messages:
                        role = "user" if msg["role"] == "user" else "assistant"
                        txt = html.escape(msg["content"])
                        st.markdown(f'<div class="msg {role}">{txt}</div>', unsafe_allow_html=True)
                        if msg.get("source"):
                            src = html.escape(msg["source"])
                            st.markdown(f'<a href="{src}" target="_blank" style="font-size:11px; margin:-8px 0 12px 0; color:#00B386;">View Source</a>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Suggestions Area (Sticky)
            st.markdown('<div class="suggestions-container">', unsafe_allow_html=True)
            st.markdown('<div class="try-asking">TRY ASKING</div>', unsafe_allow_html=True)
            cols = st.columns(len(quick_questions))
            for i, q in enumerate(quick_questions):
                if cols[i].button(q, key=f"sq_{i}"):
                    send_prompt(q)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            st.chat_input("Ask a factual question about MF schemes", key="chat_input_val", on_submit=lambda: send_prompt(st.session_state.chat_input_val))
            st.markdown('</div>', unsafe_allow_html=True)

    # --- FOOTER ---
    funds = ["Nippon India Taiwan", "ICICI Prudential ELSS", "HDFC Mid Cap", "Parag Parikh Flexi Cap", "Bandhan Small Cap", "Bluechip", "Smallcap", "Midcap"]
    marquee_items = "".join([f'<div class="marquee-item">{fund}</div>' for fund in funds])
    st.markdown(f'<div class="footer-marquee-ribbon"><div class="marquee-label">Answering For</div><div class="marquee-content">{marquee_items}{marquee_items}</div></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
