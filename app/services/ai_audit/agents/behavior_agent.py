import json
from typing import List
from app.services.ai_audit.schemas.ai_audit_schema import AgentTradeInput, DataAnalysisResult, BehaviorFinding
from app.services.ai_audit.tools.trading_metrics import analyze_sequence
from app.services.ai_audit.tools.llm_client import call_llm_json

class BehaviorAgent:
    """
    Purpose: Analyze historical risk and behavioral indicators like sequence patterns (overtrading, revenge trading).
    """
    def execute(self, trades: List[AgentTradeInput], stats: DataAnalysisResult) -> List[BehaviorFinding]:
        sequence_split = analyze_sequence(trades)
        
        # Calculate daily trade frequency
        from collections import defaultdict
        daily_trades = defaultdict(list)
        for t in trades:
            day_str = t.close_time.strftime("%Y-%m-%d") if hasattr(t.close_time, 'strftime') else str(t.close_time)[:10]
            daily_trades[day_str].append(t)
            
        overtrading_data = {}
        if daily_trades:
            # Stats for trades #1-3 vs trades #4+ across active days
            t1_3_profits = []
            t4_plus_profits = []
            for day, day_trades in daily_trades.items():
                sorted_day = sorted(day_trades, key=lambda x: x.close_time)
                for i, trade in enumerate(sorted_day):
                    if i < 3:
                        t1_3_profits.append(trade.net_profit)
                    else:
                        t4_plus_profits.append(trade.net_profit)
            
            overtrading_data = {
                "trades_1_to_3": {
                    "count": len(t1_3_profits),
                    "average_pl": round(sum(t1_3_profits)/len(t1_3_profits), 2) if t1_3_profits else 0
                },
                "trades_4_plus": {
                    "count": len(t4_plus_profits),
                    "average_pl": round(sum(t4_plus_profits)/len(t4_plus_profits), 2) if t4_plus_profits else 0
                }
            }

        prompt = f"""
        You are a trading behavior and risk analyst.
        Analyze the sequence and daily frequency statistics below.
        Identify potentially harmful or beneficial historical patterns.
        Do NOT diagnose psychology. Use evidence-based language (e.g., "Possible revenge-trading pattern detected").
        
        Data Summary:
        {stats.model_dump_json()}
        
        Sequence Performance (After Win vs After Loss):
        {json.dumps(sequence_split, indent=2)}
        
        Overtrading Indicators (1st-3rd trade vs 4th+ trade of day):
        {json.dumps(overtrading_data, indent=2)}
        
        Output a JSON object with a key "findings" containing a list of objects exactly matching this schema:
        {{
            "category": "Behavior | Risk",
            "claim": "Clear English statement of the behavior pattern",
            "severity": "Low | Medium | High | Critical",
            "evidence_stats": {{"relevant_data_points": "..."}}
        }}
        If no meaningful pattern exists, output an empty list.
        """
        
        result_json = call_llm_json(prompt)
        findings = []
        for raw in result_json.get("findings", []):
            try:
                findings.append(BehaviorFinding(**raw))
            except Exception:
                continue
        return findings
