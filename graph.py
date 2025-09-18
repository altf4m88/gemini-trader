import os
import json
from typing import TypedDict
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.outputs import LLMResult
from langgraph.graph import StateGraph, END
from agent_tools import analyze_market_state
from bybit_tools import place_market_order, close_position
from prompts_debug import system_prompt
from database import SessionLocal, TradeHistory, AgentTokenUsage

# Graph State
class GraphState(TypedDict):
    symbol: str
    interval: int
    market_analysis: str
    llm_decision: dict
    trade_executed: bool
    error_message: str

# Initialize the Gemini model
llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.environ.get("GOOGLE_API_KEY"))

# Node Functions
def analyze_market(state: GraphState):
    print("---ANALYZING MARKET---")
    symbol = state['symbol']
    interval = state['interval']
    market_analysis = analyze_market_state.invoke({"symbol": symbol, "interval": interval})
    return {"market_analysis": market_analysis}

def make_trade_decision(state: GraphState):
    print("---MAKING TRADE DECISION---")
    market_analysis = state['market_analysis']
    
    prompt = f"{system_prompt}\n\nHere is the current market analysis:\n{market_analysis}"
    
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

    # Log all decisions to the database, including HOLD
    db = SessionLocal()
    trade = TradeHistory(
        symbol=symbol,
        action=action,
        quantity=quantity,
        price=0.0,  # No price for HOLD decisions
        reasoning=reasoning,
        order_id=None,  # No order ID for HOLD decisions
        llm_decision=decision
    )
    db.add(trade)
    db.commit()
    db.close()
    
    print(f"Logged {action} decision for {symbol}")
    return {"trade_executed": False}  # Will be updated if trade is actually executed

def execute_trade(state: GraphState):
    print("---EXECUTING TRADE---")
    decision = state['llm_decision']
    action = decision.get('action')
    symbol = state['symbol']
    quantity = decision.get('quantity')
    reasoning = decision.get('reasoning')

    response = None
    if action == "BUY":
        response = place_market_order(symbol, "Buy", quantity)
    elif action == "SELL" or action == "CLOSE":
        response = close_position(symbol)

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
