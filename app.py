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

    /* Floating Action Button (FAB) */
    .fab-container {{
        position: fixed;
        bottom: 50px;
        right: 30px;
        z-index: 2001;
        cursor: pointer;
    }}

    .robot-icon {{
        width: 60px;
        height: 60px;
        background: #00B386;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}

    .robot-icon:hover {{
        transform: scale(1.1);
    }}

    /* Pulse Animation */
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(0, 179, 134, 0.7); }}
        70% {{ box-shadow: 0 0 0 15px rgba(0, 179, 134, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(0, 179, 134, 0); }}
    }}
    .pulse {{
        animation: pulse 2s infinite;
    }}

    /* Discovery Tooltip */
    .discovery-tooltip {{
        position: fixed;
        bottom: 120px;
        right: 30px;
        background: white;
        color: #44475b;
        padding: 12px 16px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        z-index: 2001;
        max-width: 240px;
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

    /* Overlay */
    .discovery-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(2px);
        z-index: 2000;
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
        z-index: 1999;
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

    /* Chat Window Styles */
    .stChatFloatingWindow {{
        position: fixed;
        bottom: 120px;
        right: 30px;
        width: 380px;
        height: 550px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.2);
        z-index: 2002;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        border: 1px solid rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def has_pii(text: str) -> bool:
    text_lower = text.lower()
    if "@" in text_lower or "aadhaar" in text_lower: return True
    if re.search(r'\bpan\b', text_lower): return True
    if re.search(r'\d{10,}', text): return True
    return False

def get_most_recent_scraped_at():
    try:
        collection = get_collection()
        results = collection.get(limit=50) 
        dates = [m.get("ingested_at", "") for m in results['metadatas'] if m.get("ingested_at")]
        if dates: return max(dates).split('T')[0]
    except: pass
    return "2026-04-18"

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

    # --- FLOATING ACTION BUTTON ---
    # Triggering state via a hidden streamlit button hack
    col1, col2 = st.columns([10, 1])
    with col2:
        # Streamlit doesn't have a direct "fixed" button, so we use a standard one and move it with CSS if needed,
        # but for reliability, we'll use a clickable HTML div that toggles session state via JS or a simple refresh.
        # However, to keep it "Streamlit-pure", we use a real button styled as a FAB.
        st.markdown('<div class="fab-container">', unsafe_allow_html=True)
        if st.button("🤖", key="fab_btn", help="Open Assistant"):
            st.session_state.chat_open = not st.session_state.chat_open
            st.session_state.discovery_seen = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- CHAT OVERLAY ---
    if st.session_state.chat_open:
        with st.sidebar: # Using Sidebar as a high-fidelity "Slide-out" chat
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
            if prompt := st.chat_input("Ask a factual question…"):
                if has_pii(prompt):
                    st.error("Please do not enter personal information.")
                else:
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.write(prompt)

                    with st.chat_message("assistant"):
                        with st.spinner("Analyzing facts..."):
                            response = run_pipeline(prompt)
                            # Extract source if exists
                            source_match = re.search(r"Source:\s*(https?://[^\s|]+)", response)
                            source_url = source_match.group(1).strip() if source_match else None
                            
                            st.write(response)
                            if source_url:
                                st.markdown(f'<small>[Click here to view source]({source_url})</small>', unsafe_allow_html=True)
                            
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response,
                                "source": source_url
                            })

    # --- BOTTOM MARQUEE ---
    schemes = [
        "ICICI Prudential ELSS Tax Saver Fund",
        "ICICI Prudential Flexicap Fund",
        "ICICI Prudential Bluechip Fund",
        "ICICI Prudential Smallcap Fund",
        "ICICI Prudential Midcap Fund"
    ]
    marquee_content = "".join([f'<div class="marquee-item">{s}</div><div class="divider"></div>' for s in schemes])
    # Duplicate for seamless loop
    marquee_html = f'<div class="marquee-container">{marquee_content}{marquee_content}</div>'

    st.markdown(f"""
    <div class="footer-ribbon">
        <div class="ribbon-label">This chatbot works for</div>
        {marquee_html}
    </div>
    """, unsafe_allow_html=True)

    # --- HIDDEN INFO ---
    if not st.session_state.chat_open:
        st.info("Click the robot icon in the bottom right to start chatting.")

if __name__ == "__main__":
    main()
