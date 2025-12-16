"""
Script to update old symbol format to new format with slashes
BTCUSD -> BTC/USD
XAUUSD -> XAU/USD
And any other symbols without slashes
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def update_symbol_format():
    """Update symbol format in existing trades"""
    
    print("🔄 Updating symbol format in trades...")
    
    # Get database credentials
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')
    
    print(f"📡 Connecting to database: {db_host}/{db_name}")
    
    # Symbol mapping - old format to new format
    symbol_mapping = {
        'BTCUSD': 'BTC/USD',
        'XAUUSD': 'XAU/USD',
        'EURUSD': 'EUR/USD',
        'GBPUSD': 'GBP/USD',
        'USDJPY': 'USD/JPY',
        'USDCHF': 'USD/CHF',
        'USDCAD': 'USD/CAD',
        'AUDUSD': 'AUD/USD',
        'NZDUSD': 'NZD/USD',
        'EURGBP': 'EUR/GBP',
        'EURJPY': 'EUR/JPY',
        'GBPJPY': 'GBP/JPY',
        'USOILUSD': 'USOIL/USD',
    }
    
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
        
        # Get all unique symbols
        print("\n1️⃣ Fetching current symbols...")
        cursor.execute("SELECT DISTINCT symbol FROM trades ORDER BY symbol")
        current_symbols = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Current symbols in database: {current_symbols}")
        
        # Update each symbol
        print("\n2️⃣ Updating symbols...")
        updated_count = 0
        
        for old_symbol, new_symbol in symbol_mapping.items():
            # Check if this symbol exists in the database
            cursor.execute("SELECT COUNT(*) FROM trades WHERE symbol = %s", (old_symbol,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"  Updating {old_symbol} -> {new_symbol} ({count} trades)")
                cursor.execute("""
                    UPDATE trades 
                    SET symbol = %s 
                    WHERE symbol = %s
                """, (new_symbol, old_symbol))
                updated_count += count
        
        # Commit changes
        conn.commit()
        
        # Verify updates
        print("\n3️⃣ Verifying updates...")
        cursor.execute("SELECT DISTINCT symbol FROM trades ORDER BY symbol")
        new_symbols = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Updated symbols: {new_symbols}")
        print(f"\n✅ Successfully updated {updated_count} trades!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Update failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

if __name__ == "__main__":
    try:
        update_symbol_format()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
