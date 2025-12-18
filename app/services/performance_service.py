from pymongo.database import Database
from datetime import datetime
import pandas as pd
from typing import Dict, Any, List

class PerformanceService:
    def __init__(self, db: Database):
        self.db = db

    def get_period_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Fetch and analyze trade data for a specific period."""
        projection = {
            "net_profit": 1,
            "close_time": 1,
            "symbol": 1,
            "mistake": 1,
            "open_time": 1,
            "_id": 0
        }
        
        cursor = self.db.trades.find({
            "user_id": user_id,
            "close_time": {"$gte": start_date, "$lt": end_date}
        }, projection).sort("close_time", 1)
        
        trades = list(cursor)
        if not trades:
            return None

        df = pd.DataFrame(trades)
        
        # Stats Calculations
        total_trades = len(df)
        wins = df[df['net_profit'] > 0]
        losses = df[df['net_profit'] <= 0]
        
        win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
        total_pl = df['net_profit'].sum()
        
        max_profit = df['net_profit'].max()
        max_loss = df['net_profit'].min()
        
        avg_win = wins['net_profit'].mean() if not wins.empty else 0
        avg_loss = losses['net_profit'].mean() if not losses.empty else 0
        
        # Profile Pairs
        symbol_groups = df.groupby('symbol')['net_profit'].sum()
        most_profitable_pair = symbol_groups.idxmax() if not symbol_groups.empty else "N/A"
        least_profitable_pair = symbol_groups.idxmin() if not symbol_groups.empty else "N/A"
        
        # Equity Curve
        equity = 0
        equity_curve = []
        for _, row in df.iterrows():
            equity += row['net_profit']
            equity_curve.append({"time": row['close_time'].strftime("%Y-%m-%d %H:%M"), "equity": float(equity)})

        stats = {
            "most_profitable_pair": most_profitable_pair,
            "least_profitable_pair": least_profitable_pair,
            "total_pl": float(total_pl),
            "max_profit_trade": float(max_profit),
            "max_loss_trade": float(max_loss),
            "avg_profit_winner": float(avg_win),
            "avg_loss_loser": float(avg_loss),
            "win_rate": float(win_rate),
            "total_trades": int(total_trades),
            "winning_trades": int(len(wins)),
            "losing_trades": int(len(losses)),
            "equity_curve": equity_curve
        }

        insights = self.generate_insights(df, stats)
        
        return {
            "stats": stats,
            "insights": insights
        }

    def generate_insights(self, df: pd.DataFrame, stats: Dict) -> Dict:
        """Generate AI-driven insights based on trading patterns."""
        insights = {
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "patterns": [],
            "mistakes": [],
            "suggestions": []
        }

        # Summary
        if stats['total_pl'] > 0:
            insights['summary'] = f"Great job! You finished the period with a total profit of ${stats['total_pl']:.2f}. Your win rate of {stats['win_rate']:.1f}% shows consistency."
        else:
            insights['summary'] = f"The period ended with a loss of ${abs(stats['total_pl']):.2f}. While setbacks happen, analyzing the patterns below will help you bounce back."

        # Strengths
        if stats['win_rate'] > 55:
            insights['strengths'].append("High accuracy in trade selection.")
        if stats['avg_profit_winner'] > abs(stats['avg_loss_loser']):
            insights['strengths'].append("Positive risk-to-reward ratio.")
        
        best_symbol = stats['most_profitable_pair']
        if best_symbol != "N/A":
             insights['strengths'].append(f"Strong performance on {best_symbol}.")

        # Weaknesses
        if stats['win_rate'] < 40:
            insights['weaknesses'].append("Low win rate - potentially overtrading or premature exits.")
        if abs(stats['avg_loss_loser']) > stats['avg_profit_winner']:
            insights['weaknesses'].append("Losses are larger than wins on average.")
        
        # Mistakes & Patterns
        if 'mistake' in df.columns:
            mistake_counts = df[df['mistake'] != 'No Mistake']['mistake'].value_counts()
            for m, count in mistake_counts.head(2).items():
                insights['mistakes'].append(f"{m} (Occurred {count} times)")
                if "Fomo" in m:
                    insights['patterns'].append("Tendency to enter trades late due to Fear Of Missing Out.")
                if "Revenge" in m:
                    insights['patterns'].append("Emotional trading after a loss.")

        # Behavioral Patterns based on time (Simplified)
        if 'open_time' in df.columns:
            df['hour'] = df['open_time'].dt.hour
            hour_perf = df.groupby('hour')['net_profit'].sum()
            if not hour_perf.empty:
                worst_hour = hour_perf.idxmin()
                if hour_perf[worst_hour] < 0:
                    insights['patterns'].append(f"Performance dips significantly around {worst_hour}:00.")

        # Suggestions
        if "Positive risk-to-reward ratio." not in insights['strengths']:
            insights['suggestions'].append("Focus on letting winners run and cutting losses faster.")
        if insights['mistakes']:
            insights['suggestions'].append("Review your entry checklist to eliminate common emotional mistakes.")
        if stats['total_trades'] > 20: # Arbitrary threshold for overtrading
             insights['suggestions'].append("Consider reducing trade frequency to focus on high-probability setups.")
        
        insights['suggestions'].append("Keep maintaining your journal; it's the key to your growth.")

        return insights
    def get_report_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Unified data for frontend report preview."""
        # 1. Get Base Data
        base_data = self.get_period_data(user_id, start_date, end_date)
        if not base_data:
            return None
            
        # 2. Get Detailed Trades for the period (with notes/mistakes)
        detailed_cursor = self.db.trades.find({
            "user_id": user_id,
            "close_time": {"$gte": start_date, "$lt": end_date}
        }).sort("close_time", -1) # Recent first
        
        trades_list = []
        for t in detailed_cursor:
            trades_list.append({
                "symbol": t.get("symbol"),
                "net_profit": t.get("net_profit", 0),
                "type": t.get("type"),
                "close_time": t.get("close_time").strftime("%Y-%m-%d %H:%M") if t.get("close_time") else "N/A",
                "mistake": t.get("mistake", "No Mistake"),
                "notes": t.get("notes", "") # The "Diary" part
            })

        # 3. Aggregate Symbol Distribution (for Pie Chart)
        df = pd.DataFrame(trades_list)
        symbol_dist = []
        if not df.empty:
            dist = df['symbol'].value_counts().to_dict()
            symbol_dist = [{"name": k, "value": v} for k, v in dist.items()]

        return {
            "stats": base_data['stats'],
            "insights": base_data['insights'],
            "trades": trades_list,
            "symbol_distribution": symbol_dist,
            "period_info": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            }
        }
