from fastapi import FastAPI
from agent_tools import analyze_market_state
import uvicorn

app = FastAPI()

@app.get("/analyze/{symbol}")
def analyze_symbol(symbol: str, interval: int = 15):
    """
    Manually trigger the analyze_market_state tool for a given symbol.
    """
    return analyze_market_state.invoke({"symbol": symbol, "interval": interval})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
