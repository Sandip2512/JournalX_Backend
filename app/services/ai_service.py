import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Using gemini-1.5-flash as the primary model
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        
        # Set up system prompt / context
        self.system_prompt = """
        You are JournalX AI, an expert trading mentor and support assistant for the JournalX trading journal application.
        
        Your capabilities:
        1. TRADING MENTOR: Explain trading concepts (Supply/Demand, risk management, indicators, psychology).
           - Be professional, concise, and encourage risk management.
           - Do not give financial advice.
        
        2. JOURNALX NAVIGATOR: Help users navigate the app.
           - "Dashboard": View weekly/monthly goals and recent activity.
           - "Journal": Log new trades manually.
           - "Analytics": detailed stats on performance.
           - "Community": Chat with other traders.
           - "Admin": System settings (if user is admin).
        
        3. PSYCHOLOGY COACH: Help users deal with tilt, fear, and greed.
           - Offer stoic, disciplined advice.
           
        4. SALES AGENT / PRODUCT EXPERT: Explain JournalX features and pricing to potential customers.
           - Highlight our unique "Execution to Excellence" philosophy.
           - JournalX Features:
             - Powerful Manual Trade Ingestion (Single/Multi-leg).
             - Deep Performance Analytics (Equity Curve, Growth Targets, Win Rate).
             - Traders Diary (Heatmap, Streaks).
             - Community (Share trades, profiles).
             
           - Subscription Plans (Accurate Pricing):
             - FREE ($0/mo): 20 trades/mo, Basic Dashboard (30 days), Current Month Diary. Perfect for beginners.
             - PRO ($5.99/mo): MOST POPULAR. Unlimited trades, Full History, Full Analytics, Goals, Community Sharing.
             - ELITE ($11.99/mo): All Pro features + AI Reports, Badges, Early Signals Access. (Mentorship coming soon).
        
        Style:
        - Professional, encouraging, concise.
        - STRICTLY FORBIDDEN: Do NOT use asterisks (*) for bullet points or bolding. 
        - USE UNICODE BULLETS (•) for all lists.
        - Do not use markdown syntax like **bold** or __italics__.
        - Keep the output clean, plain text that is easy to read.
        - Use emojis sparingly.
        """

    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini REST API directly without SDK"""
        if not self.api_key:
            return "API Key not configured."
            
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        try:
            url = self.api_url # Key now in headers
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )
            if response.status_code != 200:
                print(f"❌ Gemini API Error Body: {response.text}")
            response.raise_for_status()
            result = response.json()
            
            # Extract text from response
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return "I couldn't generate a response. Please try again."
            
        except requests.exceptions.HTTPError as http_err:
             print(f"❌ Gemini API HTTP error: {http_err}")
             return f"AI Service error (HTTP {response.status_code})"
        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            return "AI Service is currently unavailable."

    async def get_response(self, user_message: str, user_id: str = None, db: object = None) -> str:
        if not self.api_key:
            return "I'm not fully configured yet. Please check the server logs for the GEMINI_API_KEY."
            
        try:
            context_str = ""
            if user_id and db is not None:
                try:
                    # Lazy import to avoid circular dependencies
                    from app.crud.trade_crud import get_trades
                
                    # Fetch last 5 trades
                    trades = get_trades(db, user_id, skip=0, limit=5, sort_desc=True)
                    
                    # Calculate basic stats
                    all_trades_cursor = db.trades.find({"user_id": user_id})
                    all_trades = list(all_trades_cursor)
                    total_trades = len(all_trades)
                    wins = sum(1 for t in all_trades if ( (t.get('net_profit') or (t.get('profit_amount', 0) - t.get('loss_amount', 0))) > 0))
                    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                    
                    # Format trades for context
                    trades_context = "Recent Trades:\n"
                    for t in trades:
                        net = t.get('net_profit')
                        if net is None:
                            net = t.get('profit_amount', 0) - t.get('loss_amount', 0)
                        trades_context += f"- {t.get('symbol')} ({t.get('type')}): ${net:.2f} (Reason: {t.get('reason')})\n"
                    
                    context_str = f"""
                    USER CONTEXT:
                    - User ID: {user_id}
                    - Total Trades: {total_trades}
                    - Win Rate: {win_rate:.1f}%
                    {trades_context}
                    """
                except Exception as db_err:
                    print(f"⚠️ Error fetching user context: {db_err}")
                    context_str = " (Could not fetch user stats due to an error)"

            full_prompt = f"{self.system_prompt}\n\n{context_str}\n\nUser: {user_message}"
            return self._call_gemini_api(full_prompt)
            
        except Exception as e:
            return f"I encountered an error processing your request: {str(e)}"

# Singleton instance
ai_service = AIService()
