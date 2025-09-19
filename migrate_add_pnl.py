#!/usr/bin/env python3
"""
Database migration script to add PnL column to bybit_trade_history table.
Run this script to update existing database schema.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def migrate_add_pnl_column():
    """Add PnL column to existing bybit_trade_history table."""
    
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not found")
        return False
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Check if the table exists
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'bybit_trade_history'
                );
            """))
            
            table_exists = result.fetchone()[0]
            
            if not table_exists:
                print("Table 'bybit_trade_history' does not exist. Creating new table...")
                # Import and run init_db to create all tables
                from database import init_db
                init_db()
                print("All tables created successfully!")
                return True
            
            # Check if PnL column already exists
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'bybit_trade_history' 
                    AND column_name = 'pnl'
                );
            """))
            
            column_exists = result.fetchone()[0]
            
            if column_exists:
                print("PnL column already exists in bybit_trade_history table.")
                return True
            
            # Add the PnL column
            print("Adding PnL column to bybit_trade_history table...")
            connection.execute(text("""
                ALTER TABLE bybit_trade_history 
                ADD COLUMN pnl FLOAT;
            """))
            
            # Commit the transaction
            connection.commit()
            
            print("Successfully added PnL column to bybit_trade_history table!")
            
            # Now let's calculate PnL for existing records
            print("Calculating PnL for existing trade records...")
            
            # Get all existing records that don't have PnL calculated
            result = connection.execute(text("""
                SELECT id, side, exec_value, exec_fee, closed_size, category
                FROM bybit_trade_history 
                WHERE pnl IS NULL;
            """))
            
            records = result.fetchall()
            
            if records:
                print(f"Found {len(records)} records to update...")
                
                # Calculate PnL for each record
                for record in records:
                    trade_id, side, exec_value, exec_fee, closed_size, category = record
                    
                    # Use the same PnL calculation logic
                    exec_value = exec_value or 0.0
                    exec_fee = exec_fee or 0.0
                    closed_size = closed_size or 0.0
                    
                    if category and category.lower() == 'spot':
                        # For spot trades
                        if side and side.lower() == 'buy':
                            pnl = -(exec_value + exec_fee)
                        else:  # sell
                            pnl = exec_value - exec_fee
                    elif category and category.lower() in ['linear', 'inverse']:
                        # For futures trades
                        if closed_size > 0:
                            if side and side.lower() == 'sell':
                                pnl = exec_value - exec_fee
                            else:  # buy
                                pnl = -(exec_value + exec_fee)
                        else:
                            # Opening position
                            pnl = -exec_fee
                    else:
                        # Default calculation
                        if side and side.lower() == 'buy':
                            pnl = -(exec_value + exec_fee)
                        else:
                            pnl = exec_value - exec_fee
                    
                    # Update the record
                    connection.execute(text("""
                        UPDATE bybit_trade_history 
                        SET pnl = :pnl 
                        WHERE id = :trade_id;
                    """), {"pnl": round(pnl, 6), "trade_id": trade_id})
                
                connection.commit()
                print(f"Successfully calculated PnL for {len(records)} existing records!")
            else:
                print("No existing records found to update.")
            
            return True
            
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting database migration to add PnL column...")
    success = migrate_add_pnl_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now use the trade history API with PnL calculations.")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above and try again.")
