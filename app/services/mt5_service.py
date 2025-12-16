# MetaTrader5 is only available on Windows, make it optional for Linux deployment
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import time

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _ensure_mt5_initialized(max_retries: int = 3, retry_delay: float = 2.0) -> bool:
    """
    Ensure MT5 is properly initialized with retry logic.
    """
    if not MT5_AVAILABLE:
        return False
    
    for attempt in range(max_retries):
        # Check if already initialized
        if mt5.terminal_info() is not None:
            print(f"✅ MT5 already initialized")
            return True
        
        # Try to initialize
        if mt5.initialize():
            # Wait a bit for initialization to complete
            time.sleep(0.5)
            # Verify initialization
            if mt5.terminal_info() is not None:
                print(f"✅ MT5 initialized successfully")
                return True
        
        error = mt5.last_error()
        print(f"⚠️  MT5 initialization attempt {attempt + 1}/{max_retries} failed: {error}")
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    return False

def fetch_mt5_trades(account: int, password: str, server: str, days: int = 365) -> List[Dict[str, Any]]:
    """
    Fetch trades from MT5 and return as list of dictionaries.
    Handles IPC timeout errors with retry logic.
    """
    # Check if MT5 is available (only works on Windows)
    if not MT5_AVAILABLE:
        error_msg = "MetaTrader5 is not available on this system. MT5 features only work on Windows."
        logger.error(error_msg)
        raise Exception(error_msg)
    
    print(f"🔌 Attempting MT5 connection to {account}@{server}")
    
    # Ensure MT5 is initialized with retry
    if not _ensure_mt5_initialized():
        error_msg = f"MT5 initialization failed after retries. Error: {mt5.last_error()}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        raise Exception(error_msg)
    
    # Small delay to ensure connection is stable
    time.sleep(0.3)

    try:
        # First, check if account is already logged in
        account_info = mt5.account_info()
        already_logged_in = False
        
        if account_info is not None:
            # Check if the logged-in account matches what we need
            if account_info.login == account and account_info.server == server:
                print(f"✅ Account {account} is already logged in to {server}")
                already_logged_in = True
            else:
                print(f"⚠️  Different account logged in ({account_info.login}@{account_info.server}). Will attempt login to {account}@{server}")
        
        # Only login if not already logged in to the correct account
        if not already_logged_in:
            print(f"🔐 Logging into MT5 account {account}@{server}...")
            
            # Retry login up to 2 times for IPC timeout
            max_login_retries = 2
            authorized = False
            
            for login_attempt in range(max_login_retries):
                authorized = mt5.login(account, password=password, server=server)
                
                if authorized:
                    break
                
                error = mt5.last_error()
                error_code = error[0] if isinstance(error, tuple) else None
                
                # Check for IPC timeout specifically
                if error_code == -10005:
                    print(f"⚠️  IPC timeout on login attempt {login_attempt + 1}, retrying...")
                    if login_attempt < max_login_retries - 1:
                        time.sleep(2.0)  # Wait longer for IPC timeout
                        continue
                    else:
                        error_msg = "MT5 IPC timeout: Terminal is not responding. Please ensure MetaTrader 5 is running and not frozen."
                        print(f"❌ {error_msg}")
                        logger.error(error_msg)
                        # Don't shutdown - might disconnect the terminal
                        raise Exception(error_msg)
                else:
                    # Other login errors, don't retry
                    break
            
            if not authorized:
                error = mt5.last_error()
                error_msg = f"MT5 login failed. Error: {error}"
                print(f"❌ {error_msg}")
                logger.error(error_msg)
                # Don't shutdown - might disconnect the terminal
                raise Exception(error_msg)
            
            # Small delay after login to let connection stabilize
            time.sleep(0.5)
        
        # Get account info with retry for IPC timeout
        account_info = None
        for info_attempt in range(2):
            account_info = mt5.account_info()
            if account_info is not None:
                break
            
            error = mt5.last_error()
            if isinstance(error, tuple) and error[0] == -10005:
                print(f"⚠️  IPC timeout getting account info, retrying...")
                if info_attempt < 1:
                    time.sleep(2.0)
                    continue
                else:
                    error_msg = "MT5 IPC timeout: Failed to get account info. Terminal may be busy."
                    print(f"❌ {error_msg}")
                    logger.error(error_msg)
                    # Don't shutdown - might disconnect the terminal
                    raise Exception(error_msg)
        
        if account_info is None:
            error_msg = "Failed to get account info. Please ensure account is logged in to MT5 terminal."
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            # Don't shutdown - might disconnect the terminal
            raise Exception(error_msg)
        
        print(f"✅ MT5 account verified! Account: {account_info.login}")
        print(f"   Balance: {account_info.balance}")
        print(f"   Server: {account_info.server}")
        
        # Verify connection is stable before proceeding
        time.sleep(1.0)  # Wait longer to ensure connection is stable
        
        # Check if still connected before fetching history
        account_info_check = mt5.account_info()
        if account_info_check is None:
            error = mt5.last_error()
            error_msg = f"MT5 connection lost. Error: {error}. The account may have disconnected from the server. Please ensure MT5 terminal is connected to the broker server."
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            # Don't shutdown - might disconnect the terminal
            raise Exception(error_msg)
        
        # Verify we're still connected to the correct server
        if account_info_check.server != server:
            error_msg = f"MT5 server mismatch. Expected {server}, but connected to {account_info_check.server}. Please reconnect to the correct server."
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            # Don't shutdown - might disconnect the terminal
            raise Exception(error_msg)
        
        print(f"✅ Connection verified. Server: {account_info_check.server}")
        
        # Fetch deals with retry for IPC timeout
        utc_from = datetime.now() - timedelta(days=days)
        deals = None
        
        for deals_attempt in range(3):  # Increased retries
            # Check connection status before fetching
            connection_check = mt5.account_info()
            if connection_check is None:
                error = mt5.last_error()
                error_msg = f"MT5 disconnected during operation. Error: {error}. Please ensure MT5 terminal remains connected to the broker server."
                print(f"❌ {error_msg}")
                logger.error(error_msg)
                # Don't shutdown - might disconnect the terminal
                raise Exception(error_msg)
            
            deals = mt5.history_deals_get(utc_from, datetime.now())
            
            if deals is not None:
                break
            
            error = mt5.last_error()
            error_code = error[0] if isinstance(error, tuple) else None
            
            if error_code == -10005:
                print(f"⚠️  IPC timeout fetching deals (attempt {deals_attempt + 1}/3), retrying...")
                if deals_attempt < 2:
                    time.sleep(3.0)  # Wait longer for IPC timeout
                    # Try to re-verify connection
                    connection_check = mt5.account_info()
                    if connection_check is None:
                        error_msg = "MT5 disconnected during retry. Please reconnect to the broker server."
                        print(f"❌ {error_msg}")
                        logger.error(error_msg)
                        # Don't shutdown - might disconnect the terminal
                        raise Exception(error_msg)
                    continue
                else:
                    error_msg = "MT5 IPC timeout: Failed to fetch trade history after retries. Terminal may be busy or disconnected from server. Please check MT5 connection status."
                    print(f"❌ {error_msg}")
                    logger.error(error_msg)
                    # Don't shutdown - might disconnect the terminal
                    raise Exception(error_msg)
            else:
                # Other errors, don't retry
                break
        
        if deals is None:
            error = mt5.last_error()
            error_msg = f"Failed to fetch deals. Error: {error}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            # Don't shutdown - might disconnect the terminal
            raise Exception(error_msg)
        
        if len(deals) == 0:
            print("ℹ️  No trades found in history")
            return []
        
        print(f"📊 Found {len(deals)} trades")
        
        trades = []
        for deal in deals:
            try:
                trade = {
                    'ticket': deal.ticket,
                    'symbol': deal.symbol,
                    'volume': deal.volume,
                    'price_open': getattr(deal, 'price_open', deal.price),
                    'price_close': getattr(deal, 'price_close', deal.price),
                    'type': 'buy' if deal.type == 0 else 'sell',
                    'profit': deal.profit,
                    'time': datetime.fromtimestamp(deal.time) if deal.time else datetime.now(),
                    'tp': getattr(deal, 'tp', 0.0),
                    'sl': getattr(deal, 'sl', 0.0)
                }
                trades.append(trade)
            except Exception as e:
                logger.warning(f"Error processing deal {getattr(deal, 'ticket', 'unknown')}: {str(e)}")
                continue
        
        return trades
        
    except Exception as e:
        error_msg = str(e)
        # Don't add "MT5 error:" prefix if it's already a formatted error
        if not error_msg.startswith("MT5"):
            error_msg = f"MT5 error: {error_msg}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        raise Exception(error_msg)
    finally:
        # DO NOT call mt5.shutdown() - it can disconnect the account from the broker server
        # The MT5 Python API connection will be cleaned up automatically
        # Only shutdown if we explicitly need to, and never in the finally block
        print("✅ MT5 operation completed (keeping terminal connection active)")


def calculate_profit_loss(profit: float) -> tuple:
    """
    Calculate separate profit and loss amounts.
    """
    if profit >= 0:
        return profit, 0.0  # profit_amount, loss_amount
    else:
        return 0.0, abs(profit)  # profit_amount, loss_amount
