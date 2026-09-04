"""
Migration script to replace 'ticket' column with auto-incrementing 'trade_no'
For PostgreSQL database
This script preserves existing data
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_ticket_to_trade_no():
    """Migrate from ticket to trade_no column"""
    
    print("🔄 Starting migration: ticket -> trade_no (PostgreSQL)")
    
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
        
        # Check current schema
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trades'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cursor.fetchall()]
        print(f"📊 Current columns: {columns}")
        
        if 'trade_no' in columns:
            print("⚠️  Migration already applied - trade_no column exists")
            cursor.close()
            conn.close()
            return
        
        if 'ticket' not in columns:
            print("⚠️  No ticket column found - database may already be migrated")
            cursor.close()
            conn.close()
            return
        
        # Step 1: Add trade_no column (nullable first)
        print("\n1️⃣ Adding trade_no column...")
        cursor.execute("""
            ALTER TABLE trades 
            ADD COLUMN trade_no INTEGER
        """)
        print("✅ trade_no column added")
        
        # Step 2: Populate trade_no with sequential numbers
        print("\n2️⃣ Populating trade_no with sequential numbers...")
        cursor.execute("SELECT id FROM trades ORDER BY id")
        trades = cursor.fetchall()
        
        for idx, (trade_id,) in enumerate(trades, start=1):
            cursor.execute("""
                UPDATE trades 
                SET trade_no = %s 
                WHERE id = %s
            """, (idx, trade_id))
        
        print(f"✅ Populated {len(trades)} trades with sequential trade numbers")
        
        # Step 3: Make trade_no NOT NULL and UNIQUE
        print("\n3️⃣ Making trade_no NOT NULL and UNIQUE...")
        cursor.execute("""
            ALTER TABLE trades 
            ALTER COLUMN trade_no SET NOT NULL
        """)
        cursor.execute("""
            ALTER TABLE trades 
            ADD CONSTRAINT trades_trade_no_unique UNIQUE (trade_no)
        """)
        cursor.execute("""
            CREATE INDEX idx_trades_trade_no ON trades(trade_no)
        """)
        print("✅ Constraints and index added")
        
        # Step 4: Drop ticket column
        print("\n4️⃣ Dropping ticket column...")
        cursor.execute("""
            ALTER TABLE trades 
            DROP COLUMN ticket
        """)
        print("✅ ticket column removed")
        
        # Commit all changes
        conn.commit()
        
        # Verify migration
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trades'
            ORDER BY ordinal_position
        """)
        new_columns = [row[0] for row in cursor.fetchall()]
        print(f"\n📊 New columns: {new_columns}")
        
        if 'trade_no' in new_columns and 'ticket' not in new_columns:
            print("✅ Verification passed: trade_no exists, ticket removed")
            print(f"✅ Migration completed successfully!")
            print(f"📈 Total trades migrated: {len(trades)}")
        else:
            print("⚠️  Verification warning: Please check the schema")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

if __name__ == "__main__":
    try:
        migrate_ticket_to_trade_no()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
