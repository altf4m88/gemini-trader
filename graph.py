import os
import json
from typing import TypedDict
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.outputs import LLMResult
from langgraph.graph import StateGraph, END
from agent_tools import analyze_market_state
from bybit_tools import spot_place_market_order, spot_close_position, perp_place_market_order, perp_close_position
from prompts_debug import system_prompt
from prompts import spot_system_prompt, perp_system_prompt
from database import SessionLocal, TradeHistory, AgentTokenUsage

# Graph State
class GraphState(TypedDict):
    symbol: str
    interval: int
    market_analysis: str
    llm_decision: dict
    trade_executed: bool
    error_message: str
    trading_mode: str  # "spot" or "perp"

# Initialize the Gemini model
llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.environ.get("GOOGLE_API_KEY"))

# Node Functions
def analyze_market(state: GraphState):
    print("---ANALYZING MARKET---")
    symbol = state['symbol']
    interval = state['interval']
    trading_mode = state.get('trading_mode', 'spot')
    
    market_analysis = analyze_market_state.invoke({
        "symbol": symbol, 
        "interval": interval,
        "trading_mode": trading_mode
    })
    return {"market_analysis": market_analysis}

def make_trade_decision(state: GraphState):
    print("---MAKING TRADE DECISION---")
    market_analysis = state['market_analysis']
    trading_mode = state.get('trading_mode', 'spot')
    
    # Select the appropriate prompt based on trading mode
    if trading_mode == 'spot':
        selected_prompt = spot_system_prompt
    elif trading_mode == 'perp':
        selected_prompt = perp_system_prompt
    else:
        # Fallback to debug prompt for testing
        selected_prompt = system_prompt
    
    prompt = f"{selected_prompt}\n\nHere is the current market analysis:\n{market_analysis}"
    
    # Use generate to get token usage
    llm_result: LLMResult = llm.generate([prompt])
    response_text = llm_result.generations[0][0].text
    
    # Log token usage
    if llm_result.llm_output and 'token_usage' in llm_result.llm_output:
        token_usage = llm_result.llm_output['token_usage']
        db = SessionLocal()
        db_token_usage = AgentTokenUsage(
            model_name="gemini-pro",
            input_tokens=token_usage.get('prompt_total_tokens', 0),
            output_tokens=token_usage.get('candidates_total_tokens', 0),
            total_tokens=token_usage.get('total_tokens', 0)
        )
        db.add(db_token_usage)
        db.commit()
        db.close()

    # Try to parse JSON directly first
    try:
        decision = json.loads(response_text)
        return {"llm_decision": decision}
    except json.JSONDecodeError:
        # Try to extract JSON from the response if it's wrapped in other text
        try:
            # Look for JSON object within the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                decision = json.loads(json_str)
                print(f"Extracted JSON from response: {json_str}")
                return {"llm_decision": decision}
            else:
                print("No JSON object found in response")
                return {"error_message": f"No valid JSON found in LLM response: {response_text}"}
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return {"error_message": f"Failed to decode LLM response as JSON: {response_text}"}

def log_decision(state: GraphState):
    print("---LOGGING DECISION---")
    decision = state['llm_decision']
    action = decision.get('action')
    symbol = state['symbol']
    quantity = decision.get('quantity')
    reasoning = decision.get('reasoning')
    trading_mode = state.get('trading_mode', 'spot')

    # Log all decisions to the database, including HOLD
    db = SessionLocal()
    trade = TradeHistory(
        symbol=f"{symbol}_{trading_mode}",  # Include trading mode in symbol
        action=action,
        quantity=quantity,
        price=0.0,  # No price for HOLD decisions
        reasoning=f"[{trading_mode.upper()}] {reasoning}",  # Add mode to reasoning
        order_id=None,  # No order ID for HOLD decisions
        llm_decision=decision
    )
    db.add(trade)
    db.commit()
    db.close()
    
    print(f"Logged {action} decision for {symbol} in {trading_mode.upper()} mode")
    return {"trade_executed": False}  # Will be updated if trade is actually executed

def execute_trade(state: GraphState):
    print("---EXECUTING TRADE---")
    decision = state['llm_decision']
    action = decision.get('action')
    symbol = state['symbol']
    quantity = decision.get('quantity')
    reasoning = decision.get('reasoning')
    trading_mode = state.get('trading_mode', 'spot')  # Default to spot if not specified

    # Safety check: Prevent opening new positions when one already exists
    if trading_mode == 'perp' and action in ["BUY", "SELL"]:
        from bybit_tools import perp_get_open_positions
        existing_position = perp_get_open_positions(symbol)
        if existing_position and existing_position.get('has_position', False):
            print(f"⚠️  SAFETY CHECK: Cannot open new {action} position - existing position detected!")
            print(f"   Existing: {existing_position['side']} {existing_position['size']} units")
            print(f"   Skipping trade execution for safety.")
            return {"trade_executed": False, "error_message": f"Position already exists: {existing_position['side']} {existing_position['size']} units"}
    
    elif trading_mode == 'spot' and action == "BUY":
        from bybit_tools import spot_get_open_positions
        existing_position = spot_get_open_positions(symbol)
        if existing_position and existing_position.get('has_position', False):
            print(f"⚠️  SAFETY CHECK: Cannot open new {action} position - existing position detected!")
            print(f"   Existing: {existing_position['size']} units")
            print(f"   Skipping trade execution for safety.")
            return {"trade_executed": False, "error_message": f"Position already exists: {existing_position['size']} units"}

    response = None
    if trading_mode == 'spot':
        # Use spot trading functions
        if action == "BUY":
            response = spot_place_market_order(symbol, "Buy", quantity)
        elif action == "SELL" or action == "CLOSE":
            response = spot_close_position(symbol)
    elif trading_mode == 'perp':
        # Use perpetual futures trading functions
        if action == "BUY":
            response = perp_place_market_order(symbol, "Buy", quantity, margin_usd=50.0, leverage=10)
        elif action == "SELL":
            response = perp_place_market_order(symbol, "Sell", quantity, margin_usd=50.0, leverage=10)
        elif action == "CLOSE_LONG" or action == "CLOSE_SHORT" or action == "CLOSE":
            response = perp_close_position(symbol)
    else:
        return {"error_message": f"Invalid trading mode: {trading_mode}"}

    if response and response.get('retCode') == 0:
        # Update the existing database record with execution details
        db = SessionLocal()
        # Get the most recent trade record for this symbol
        trade = db.query(TradeHistory).filter(
            TradeHistory.symbol == symbol,
            TradeHistory.action == action
        ).order_by(TradeHistory.timestamp.desc()).first()
        
        if trade:
            trade.price = float(response['result'].get('avgPrice', 0.0))
            trade.order_id = response['result'].get('orderId')
            db.commit()
        db.close()
        return {"trade_executed": True}
    elif response:
        return {"error_message": f"Failed to execute {action} order: {response.get('retMsg')}"}
    
    return {"trade_executed": False}


# Conditional Edge Logic
def should_execute_trade(state: GraphState):
    action = state.get("llm_decision", {}).get("action")
    if action in ["BUY", "SELL", "CLOSE"]:
        return "execute_trade"
    else: # HOLD or no action
        return END

# Graph Construction
workflow = StateGraph(GraphState)

workflow.add_node("analyze_market", analyze_market)
workflow.add_node("make_trade_decision", make_trade_decision)
workflow.add_node("log_decision", log_decision)
workflow.add_node("execute_trade", execute_trade)

workflow.set_entry_point("analyze_market")
workflow.add_edge("analyze_market", "make_trade_decision")
workflow.add_edge("make_trade_decision", "log_decision")
workflow.add_conditional_edges(
    "log_decision",
    should_execute_trade,
    {
        "execute_trade": "execute_trade",
        END: END
    }
)
workflow.add_edge("execute_trade", END)

app = workflow.compile()
