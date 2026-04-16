import streamlit as st
import re
from app.pipeline import run_pipeline, get_collection
from app.refusal import DISCLAIMER

def get_most_recent_scraped_at():
    """Retrieve the most recent 'ingested_at' date from ChromaDB."""
    try:
        collection = get_collection()
        # Get a chunk of metadata to find the most recent
        results = collection.get(limit=100) 
        if not results or not results.get('metadatas'):
            return "Unknown"
        dates = [m.get("ingested_at", "") for m in results['metadatas'] if m.get("ingested_at")]
        if dates:
            d = max(dates)
            return d.split('T')[0]
    except Exception as e:
        print(f"Error fetching from ChromaDB: {e}")
    return "Unknown"

def has_pii(text: str) -> bool:
    """Check text for PII markers: '@', 'aadhaar', 'pan' (word), or 10+ digits."""
    text_lower = text.lower()
    if "@" in text_lower:
        return True
    if "aadhaar" in text_lower:
        return True
    # Match 'pan' exactly as a whole word to avoid tripping on 'company', 'apan', etc.
    if re.search(r'\bpan\b', text_lower):
        return True
    # Match any continuous sequence of 10 or more digits
    if re.search(r'\d{10,}', text):
        return True
    return False

def main():
    # 1. Title
    st.title("ICICI Prudential MF — FAQ Assistant")
    
    # 2. Subtitle
    st.markdown("<small>Facts only. No investment advice.</small>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Initialize query state for button population
    if "query_text" not in st.session_state:
        st.session_state.query_text = ""

    def update_query(new_query):
        st.session_state.query_text = new_query

    # 3. Example question buttons
    st.write("#### Try an example:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("What is the expense ratio of ICICI Bluechip Fund?", 
                  on_click=update_query, 
                  args=("What is the expense ratio of ICICI Bluechip Fund?",))
    with col2:
        st.button("What is the lock-in period for the ELSS fund?", 
                  on_click=update_query, 
                  args=("What is the lock-in period for the ELSS fund?",))
    with col3:
        st.button("What is the NAV of the Midcap fund?", 
                  on_click=update_query, 
                  args=("What is the NAV of the Midcap fund?",))
        
    st.markdown("<hr>", unsafe_allow_html=True)

    # 4. Text input box
    query = st.text_input("Ask a factual question", value=st.session_state.query_text)
    
    # 5. Submit button
    if st.button("Submit"):
        # Clear specific PII logic first
        if has_pii(query):
            # Clear it immediately explicitly by zeroing out the variable in next render
            st.session_state.query_text = "" 
            st.error("Please do not enter personal information.")
            st.stop()
            
        if not query.strip():
            st.warning("Please enter a factual question.")
            st.stop()
            
        with st.spinner("Generating facts..."):
            # 6. Call run_pipeline and display in grey info box
            response = run_pipeline(query)
            st.info(response)
            
            # 7. Below the response, show the source URL as a clickable hyperlink
            # Assumes format "Source: [url]" as dictated by prompt rules
            match = re.search(r"Source:\s*(https?://[^\s|]+)", response)
            if match:
                url = match.group(1).strip()
                st.markdown(f"**References:** [Click here to view source]({url})")

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 8. Footer disclaimer
    st.caption(DISCLAIMER)
    
    # 9. Small text at the bottom for latest scrape date
    recent_date = get_most_recent_scraped_at()
    st.markdown(f"<small>Last updated from sources: {recent_date}</small>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
