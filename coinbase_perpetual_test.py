"""
MIT License

Copyright (c) 2024 Lukas Meienberger

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software, to use, copy, modify, and distribute it without restriction,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

Disclaimer:
This software uses the Coinbase REST API. Usage of this software must comply
with Coinbase's API terms of service. The author is not affiliated with Coinbase,
and this script is provided independently of Coinbase, for educational and informational purposes only.
"""

# =====================
# DISCLAIMER
# =====================
# 1. Create an API key with permissions for perpetual futures trading ('can_view', 'can_trade').
# 2. Transfer a small amount of USDC (e.g., 30 USD) to your perpetual wallet.
# 3. Install the required packages: `pip install coinbase-advanced-py`.
# 4. Use at your own risk. Ensure you understand the implications of leveraged trading.

# =====================
# IMPORTS
# =====================

import os
import time
import uuid
from coinbase.rest import RESTClient

# =====================
# CONFIGURATION
# =====================

# Coinbase API credentials
API_KEY = os.getenv("COINBASE_API_KEY", "organizations/xxxxx")
API_SECRET = os.getenv("COINBASE_API_SECRET", "-----BEGIN EC PRIVATE KEY-----xxxxx-----END EC PRIVATE KEY-----\n")

# Proxy settings (optional)
proxy_list = [
    {"address": "192.168.1.1", "port": 5000, "username": "xxxxx", "password": "xxxxx"}
]

# =====================
# HELPER FUNCTIONS
# =====================

def set_proxy(enable_proxy=False):
    """
    Optionally sets a proxy from the proxy list if enabled.
    """
    if enable_proxy:
        proxy = proxy_list[0]  # Use the first proxy in the list
        proxy_url = f"socks5h://{proxy['username']}:{proxy['password']}@{proxy['address']}:{proxy['port']}"

        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        print(f"Proxy set: {proxy_url}")
    else:
        print("Proxy is disabled.")
        
# Helper function to print portfolio details
def print_portfolio_details(details, label="Portfolio Overview"):
    print(f"\n=== {label} ===")
    print(f"Collateral:          {details['collateral']:.2f} USDC")
    print(f"Unrealized PnL:      {details['unrealized_pnl']:.2f} USDC")
    print(f"Buying Power:        {details['buying_power']:.2f} USDC")
    print(f"Total Balance:       {details['total_balance']:.2f} USDC")
    print(f"Max Withdrawal:      {details['max_withdrawal_amount']:.2f} USDC")

# Helper function to print positions
def print_positions(positions, label="Current Positions"):
    print(f"\n=== {label} ===")
    if not positions:
        print("No open positions.")
        return
    print("{:<15} {:<10} {:<15} {:<10} {:<10}".format(
        "Symbol", "Net Size", "Unrealized PnL", "VWAP", "Leverage"
    ))
    print("-" * 60)
    for pos in positions:
        print("{:<15} {:<10.3f} {:<15.2f} {:<10.2f} {:<10.1f}".format(
            pos['symbol'], pos['net_size'], pos['unrealized_pnl'],
            pos['vwap'], pos['leverage']
        ))

# =====================
# API FUNCTIONS
# =====================

# Function to fetch key permissions
def get_key_permissions():
    try:
        response = client.get("/api/v3/brokerage/key_permissions")
        print("Permissions:", response)
        return response
    except Exception as e:
        print(f"Error fetching key permissions: {e}")
        return None

# Function to fetch portfolio UUID by name
def get_portfolio_uuid(portfolio_name):
    try:
        accounts_response = client.get_accounts()
        print("Accounts response:", accounts_response)

        # Convert response to a dictionary if it's an object
        accounts = accounts_response.accounts if hasattr(accounts_response, 'accounts') else accounts_response.get('accounts', [])

        # Search for the portfolio with the given name
        for account in accounts:
            if account['name'] == portfolio_name and account['platform'] == "ACCOUNT_PLATFORM_INTX":
                return account['retail_portfolio_id']
        print(f"Portfolio with name {portfolio_name} not found or inaccessible.")
    except Exception as e:
        print(f"Error while fetching portfolio ID: {e}")
    return None

# Function to fetch portfolio details
def get_portfolio_details(portfolio_uuid):
    try:
        response = client.get(f"/api/v3/brokerage/intx/portfolio/{portfolio_uuid}")
        summary = response.get("summary", {})
        return {
            "collateral": float(summary.get("collateral", {}).get("value", 0)),
            "unrealized_pnl": float(summary.get("unrealized_pnl", {}).get("value", 0)),
            "buying_power": float(summary.get("buying_power", {}).get("value", 0)),
            "total_balance": float(summary.get("total_balance", {}).get("value", 0)),
            "max_withdrawal_amount": float(summary.get("max_withdrawal_amount", {}).get("value", 0))
        }
    except Exception as e:
        print(f"Error fetching portfolio details: {e}")
        return None

# Function to fetch open positions
def list_positions(portfolio_uuid):
    try:
        response = client.get(f"/api/v3/brokerage/intx/positions/{portfolio_uuid}")
        positions = response.get("positions", [])
        formatted_positions = []
        for position in positions:
            formatted_positions.append({
                "symbol": position.get("symbol"),
                "net_size": float(position.get("net_size", 0)),
                "unrealized_pnl": float(position.get("unrealized_pnl", {}).get("value", 0)),
                "vwap": float(position.get("vwap", {}).get("value", 0)),
                "leverage": float(position.get("leverage", 1))
            })
        return formatted_positions
    except Exception as e:
        print(f"Error fetching positions: {e}")
        return []

# Function to place a limit order
def create_limit_order(product_id, limit_price, base_size, side, portfolio_uuid, leverage=None, margin_type="CROSS"):
    try:
        order_data = {
            "client_order_id": str(uuid.uuid4()),
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": {
                "limit_limit_gtc": {
                    "base_size": str(base_size),
                    "limit_price": str(limit_price)
                }
            },
            "retail_portfolio_id": portfolio_uuid
        }
        if leverage:
            order_data["leverage"] = str(leverage)
        order_data["margin_type"] = margin_type.upper()

        response = client.post("/api/v3/brokerage/orders", data=order_data)
        print("Order Response:", response)
        return response
    except Exception as e:
        print(f"Error creating limit order: {e}")
        return None

# Function to place a market order
def create_market_order(product_id, base_size, side, portfolio_uuid, leverage=None, margin_type="CROSS"):
    try:
        order_data = {
            "client_order_id": str(uuid.uuid4()),
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": {
                "market_market_ioc": {
                    "base_size": str(base_size)
                }
            },
            "retail_portfolio_id": portfolio_uuid
        }
        if leverage:
            order_data["leverage"] = str(leverage)
        order_data["margin_type"] = margin_type.upper()

        response = client.post("/api/v3/brokerage/orders", data=order_data)
        print("Market Order Response:", response)
        return response
    except Exception as e:
        print(f"Error creating market order: {e}")
        return None

# Function to cancel orders
def cancel_orders(order_ids):
    try:
        response = client.post("/api/v3/brokerage/orders/batch_cancel", data={"order_ids": order_ids})
        print("Cancel Order Response:", response)
        return response
    except Exception as e:
        print(f"Error cancelling orders: {e}")
        return None

# Function to fetch market price
def get_market_price(product_id):
    try:
        response = client.get(f"/api/v3/brokerage/products/{product_id}/ticker")
        trades = response.get("trades", [])
        if trades:
            return float(trades[0]["price"])
        print("No trades available.")
        return None
    except Exception as e:
        print(f"Error fetching market price: {e}")
        return None

# Function to reduce positions
def reduce_position(product_id, side, size, portfolio_uuid):
    try:
        order_data = {
            "client_order_id": str(uuid.uuid4()),
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": {
                "market_market_ioc": {
                    "base_size": str(size)
                }
            },
            "retail_portfolio_id": portfolio_uuid
        }
        response = client.post("/api/v3/brokerage/orders", data=order_data)
        print("Reduce Position Response:", response)
        return response
    except Exception as e:
        print(f"Error reducing position: {e}")
        return None

# =====================
# MAIN EXECUTION
# =====================
if __name__ == "__main__":
    # Initialize RESTClient
    set_proxy(enable_proxy=False)  # Set to True to enable proxy
    client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

    portfolio_name = "USDC Wallet"
    product_id = "BTC-PERP-INTX"

    # Fetch portfolio UUID
    portfolio_uuid = get_portfolio_uuid(portfolio_name)
    if not portfolio_uuid:
        print("Failed to retrieve portfolio UUID.")
        exit()

    # Fetch and print initial portfolio details
    portfolio_details = get_portfolio_details(portfolio_uuid)
    if not portfolio_details:
        print("Failed to retrieve portfolio details.")
        exit()
    print_portfolio_details(portfolio_details, label="Initial Portfolio Overview")

    # Get market price
    market_price = get_market_price(product_id)
    if not market_price:
        print("Failed to fetch market price.")
        exit()
    print(f"\nMarket Price for {product_id}: {market_price:.2f} USDC")

    # Calculate order parameters
    leverage = 10
    max_withdrawal = portfolio_details["max_withdrawal_amount"]
    base_size = int((leverage * max_withdrawal * 0.5) / market_price * 1000) / 1000
    limit_price = int(market_price * 0.995 * 10) / 10
    print(f"\nOrder Parameters:\n  Leverage: {leverage}\n  Base Size: {base_size}\n  Limit Price: {limit_price:.1f}")

    # Place limit order
    print("\nPlacing Limit Buy Order...")
    order_response = create_limit_order(product_id, limit_price, base_size, "BUY", portfolio_uuid, leverage)
    if order_response and order_response.get("success"):
        print("Limit Order placed successfully!")
        portfolio_details = get_portfolio_details(portfolio_uuid)
        print_portfolio_details(portfolio_details, label="Portfolio After Limit Order")

        # Extract order ID and cancel it as an example
        order_id = order_response.get("success_response", {}).get("order_id")
        if order_id:
            time.sleep(2)
            print("\nCancelling the Limit Order...")
            cancel_orders([order_id])
            print("Order cancelled successfully.")
    else:
        print("Limit Order placement failed.")

    # Place market order
    print("\nPlacing Market Buy Order...")
    market_order_response = create_market_order(product_id, base_size, "BUY", portfolio_uuid, leverage)
    if market_order_response and market_order_response.get("success"):
        print("Market Order placed successfully!")
        portfolio_details = get_portfolio_details(portfolio_uuid)
        print_portfolio_details(portfolio_details, label="Portfolio After Market Order")
    else:
        print("Market Order placement failed.")

    # Fetch and print current positions
    positions = list_positions(portfolio_uuid)
    print_positions(positions)

    # Reduce position example
    if positions:
        print("\nReducing Position...")
        reduce_position(product_id, "SELL", positions[0]["net_size"], portfolio_uuid)
        portfolio_details = get_portfolio_details(portfolio_uuid)
        print_portfolio_details(portfolio_details, label="Portfolio After Reducing Position")
