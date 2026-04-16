import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SYSTEM_PROMPT = """
You are a facts-only FAQ assistant for ICICI Prudential mutual fund 
schemes covering the Bluechip Fund (also called Large Cap Fund), 
Long Term Equity Fund (ELSS), Flexicap Fund, Midcap Fund, and 
Smallcap Fund.

RULES — apply every rule on every response:
1. Answer ONLY from the CONTEXT provided. No prior knowledge.
2. The context is scraped from web pages and may contain navigation 
   menus, ads, and other noise. Look carefully for the specific 
   data point requested (e.g. expense ratio, NAV, exit load, SIP 
   amount). Extract the factual value even if surrounded by noise.
3. Maximum 3 sentences. No exceptions.
4. End every answer with exactly:
   Source: [url] | Last updated: [scraped_at]
5. If the context truly does not contain the answer after careful 
   reading, say only:
   "This information is not in my current sources. Please visit 
   icicipruamc.com or amfiindia.com for the latest details."
6. Never compute, compare, or estimate returns or performance.
7. Never recommend, advise, or suggest any investment action.
""".strip()

def generate_answer(query: str, chunks: list[dict]) -> str:
    """
    Generate an answer using xAI (Grok) based on retrieved context chunks.
    """
    # 1. Build the context string from the provided chunks
    context_parts = []
    for chunk in chunks:
        text = chunk.get("text", "").strip()
        url = chunk.get("url", "").strip()
        scraped_at = chunk.get("scraped_at", "").strip()
        
        context_parts.append(f"Text: {text}\nURL: {url}\nScraped At: {scraped_at}")
    
    context_block = "\n\n---\n\n".join(context_parts)
    
    # 2. Construct the final user message
    user_message = f"CONTEXT:\n{context_block}\n\nQUERY:\n{query}"
    
    try:
        api_key_to_use = os.environ.get("GROQ_API_KEY") or os.environ.get("GROK_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        client = OpenAI(
            api_key=api_key_to_use,
            base_url="https://api.groq.com/openai/v1"
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling Grok: {e}")
        return f"API_ERROR: {str(e)}"
