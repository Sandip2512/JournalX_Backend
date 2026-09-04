"""
Script to re-sequence trade_no to ensure proper sequential numbering from 1
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def resequence_trade_numbers():
    """Re-sequence trade_no to be 1, 2, 3, ... in order"""
    
    print("🔄 Re-sequencing trade numbers...")
    
    # Get database credentials
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')
    
    print(f"📡 Connecting to database: {db_host}/{db_name}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        conn.autocommit = False
        cursor = conn.cursor()
        
        # Get all trades ordered by creation (id or open_time)
        print("\n1️⃣ Fetching all trades...")
        cursor.execute("""
            SELECT id, trade_no, symbol, open_time 
            FROM trades 
            ORDER BY open_time, id
        """)
        trades = cursor.fetchall()
        
        print(f"📊 Found {len(trades)} trades")
        print("\nCurrent trade numbers:")
        for trade in trades:
            print(f"  ID: {trade[0]}, Trade No: {trade[1]}, Symbol: {trade[2]}, Time: {trade[3]}")
        
        # Temporarily drop the unique constraint
        print("\n2️⃣ Temporarily removing unique constraint...")
        cursor.execute("""
            ALTER TABLE trades 
            DROP CONSTRAINT IF EXISTS trades_trade_no_unique
        """)
        
        # Re-assign sequential numbers
        print("\n3️⃣ Re-assigning sequential trade numbers (1, 2, 3, ...)...")
        for new_trade_no, (trade_id, old_trade_no, symbol, open_time) in enumerate(trades, start=1):
            cursor.execute("""
                UPDATE trades 
                SET trade_no = %s 
                WHERE id = %s
            """, (new_trade_no, trade_id))
            print(f"  ✓ Trade ID {trade_id} ({symbol}): {old_trade_no} → {new_trade_no}")
        
        # Re-add the unique constraint
        print("\n4️⃣ Re-adding unique constraint...")
        cursor.execute("""
            ALTER TABLE trades 
            ADD CONSTRAINT trades_trade_no_unique UNIQUE (trade_no)
        """)
        
        # Commit all changes
        conn.commit()
        
        # Verify the new sequence
        print("\n5️⃣ Verifying new sequence...")
        cursor.execute("""
            SELECT id, trade_no, symbol, open_time 
            FROM trades 
            ORDER BY trade_no
        """)
        updated_trades = cursor.fetchall()
        
        print("\n✅ New trade numbers:")
        for trade in updated_trades:
            print(f"  Trade No: {trade[1]}, ID: {trade[0]}, Symbol: {trade[2]}, Time: {trade[3]}")
        
        # Check for gaps
        trade_numbers = [t[1] for t in updated_trades]
        expected = list(range(1, len(updated_trades) + 1))
        
        if trade_numbers == expected:
            print(f"\n✅ Perfect! Trade numbers are sequential from 1 to {len(updated_trades)}")
        else:
            print(f"\n⚠️  Warning: Trade numbers are not perfectly sequential")
            print(f"   Expected: {expected}")
            print(f"   Got: {trade_numbers}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 Re-sequencing completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Re-sequencing failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

if __name__ == "__main__":
    try:
        resequence_trade_numbers()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
