import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        self.chat = None
        
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

    def _initialize(self):
        """Lazy initialization of Gemini to prevent startup blocking"""
        if not self.model and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Using gemini-1.5-flash for better speed and stability
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.chat = self.model.start_chat(history=[])
                print("✅ Gemini AI Service Initialized (Model: gemini-1.5-flash)")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini: {e}")
                try:
                    # Attempt to list models to help debugging
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    print(f"📋 Available models for your API key: {models}")
                except Exception as list_err:
                    print(f"❌ Could not list models: {list_err}")

    async def get_response(self, user_message: str, user_id: str = None, db: object = None) -> str:
        if not self.api_key:
            return "I'm not fully configured yet. Please check the server logs for the GEMINI_API_KEY."
        
        # Ensure initialized
        if not self.model:
            self._initialize()
            if not self.model:
                return "AI Service is currently unavailable (Initialization Failed)."
            
        try:
            context_str = ""
            if user_id and db is not None:
                try:
                    from app.crud.trade_crud import get_trades
                
                    # Fetch last 5 trades
                    trades = get_trades(db, user_id, skip=0, limit=5, sort_desc=True)
                    
                    # Calculate basic stats (simple approximation)
                    all_trades_cursor = db.trades.find({"user_id": user_id})
                    all_trades = list(all_trades_cursor)
                    total_trades = len(all_trades)
                    wins = sum(1 for t in all_trades if (t.get('profit_amount', 0) - t.get('loss_amount', 0)) > 0)
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
                
            # Use generate_content for stateless
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"I encountered an error processing your request: {str(e)}"

# Singleton instance
ai_service = AIService()
