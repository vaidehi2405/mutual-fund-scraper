import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

FACTUAL_KEYWORDS = [
    "expense ratio", "ter", "exit load", "minimum sip", "lock-in", "lock in", 
    "riskometer", "benchmark", "download statement", "capital gains", 
    "minimum investment", "fund manager", "aum", "nav"
]

ADVISORY_KEYWORDS = [
    "should i", "which is better", "recommend", "returns", "will it grow", 
    "good investment", "buy", "sell", "portfolio", "predict", "which fund", 
    "better fund"
]

def classify_query(query: str) -> str:
    query_lower = query.lower()
    
    # Check factual keywords
    for kw in FACTUAL_KEYWORDS:
        if kw in query_lower:
            return "FACTUAL"
            
    # Check advisory keywords
    for kw in ADVISORY_KEYWORDS:
        if kw in query_lower:
            return "ADVISORY"
            
    # If neither matches, fallback to Grok API
    try:
        from openai import OpenAI
        
        api_key_to_use = os.environ.get("GROQ_API_KEY") or os.environ.get("GROK_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        client = OpenAI(
            api_key=api_key_to_use, 
            base_url="https://api.groq.com/openai/v1"
        )
        
        prompt = f"Classify this mutual fund query as FACTUAL or ADVISORY. \nReply with one word only. Query: {query}"
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        
        return response.choices[0].message.content.strip().upper()
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "UNKNOWN"

def detect_topic(query: str) -> str:
    query_lower = query.lower()
    
    if "expense ratio" in query_lower or "ter" in query_lower:
        return "expense_ratio"
    if "exit load" in query_lower:
        return "exit_load"
    if any(k in query_lower for k in ["lock-in", "lock in", "lockin"]):
        return "lock_in"
    if "sip" in query_lower or "minimum sip" in query_lower:
        return "min_sip"
    if "riskometer" in query_lower:
        return "riskometer"
    if "benchmark" in query_lower:
        return "benchmark"
    if any(k in query_lower for k in ["statement", "capital gains", "download"]):
        return "statement_download"
    if "nav" in query_lower:
        return "nav"
        
    return "general"

def detect_scheme(query: str) -> str:
    query_lower = query.lower()
    
    if any(k in query_lower for k in ["bluechip", "large cap", "largecap"]):
        return "large_cap"
    if any(k in query_lower for k in ["flexicap", "flexi cap", "flexible"]):
        return "flexicap"
    if any(k in query_lower for k in ["midcap", "mid cap"]):
        return "midcap"
    if any(k in query_lower for k in ["smallcap", "small cap"]):
        return "small_cap"
    if any(k in query_lower for k in ["elss", "tax saver", "long term equity", "80c"]):
        return "elss"
        
    return "all"
