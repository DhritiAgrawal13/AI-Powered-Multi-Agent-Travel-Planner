"""
Simple ADK-style Multi-Agent Travel Planner (single-file)
- Lightweight prototype for demo / course submission (Option A)
- Agents: Planner, Search (fake), Budget, Summarizer
- Frontend served from same file (no Node/Vite)
- Run: python simple_travel_planner.py
  or: uvicorn simple_travel_planner:app --reload
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import random
import time
import uuid
import logging
from typing import Dict, Any, List

# ----------------------------
# Logging & simple metrics
# ----------------------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger("simple_travel_planner")

METRICS = {"plans_created": 0, "agent_calls": 0}

# ----------------------------
# FastAPI app + CORS
# ----------------------------
app = FastAPI(title="Simple Travel Planner (Prototype)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Simple frontend (served by same app)
# ----------------------------
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Simple Travel Planner</title>
  <style>
    body{font-family:Arial,background:#f4f6f8;padding:20px}
    .box{max-width:700px;margin:30px auto;padding:20px;background:#fff;border-radius:10px;box-shadow:0 6px 18px rgba(0,0,0,0.06)}
    input,button{width:100%;padding:10px;margin:8px 0;border-radius:8px;border:1px solid #ddd}
    pre{background:#f0f0f0;padding:12px;border-radius:8px;overflow:auto}
    .row{display:flex;gap:8px}
    .row > input{flex:1}
  </style>
</head>
<body>
  <div class="box">
    <h2>🧭 Simple Multi-Agent Travel Planner</h2>
    <div class="row">
      <input id="from_city" placeholder="From city" />
      <input id="to_city" placeholder="To city" />
    </div>
    <div class="row">
      <input id="budget" placeholder="Budget (number)" />
      <input id="days" placeholder="Duration (days)" />
    </div>
    <button onclick="createPlan()">Generate Plan</button>
    <h3>Result</h3>
    <pre id="result">(no result)</pre>
  </div>

  <script>
    async function createPlan(){
      const body = {
        from_city: document.getElementById('from_city').value || '',
        to_city: document.getElementById('to_city').value || '',
        budget: parseInt(document.getElementById('budget').value || '0'),
        days: parseInt(document.getElementById('days').value || '3')
      };
      const res = await fetch('/plan', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      const j = await res.json();
      document.getElementById('result').innerText = JSON.stringify(j, null, 2);
    }
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def homepage():
    return INDEX_HTML

# ----------------------------
# Request/response models
# ----------------------------
class PlanRequest(BaseModel):
    from_city: str
    to_city: str
    budget: int
    days: int

# ----------------------------
# Agent implementations (lightweight)
# ----------------------------
async def planner_agent(req: PlanRequest) -> Dict[str, Any]:
    METRICS["agent_calls"] += 1
    logger.info(f"[Planner] Creating tasks for trip {req.from_city} -> {req.to_city}")
    # Break request into simple tasks (strings)
    tasks = {
        "flight_query": f"cheap flights from {req.from_city} to {req.to_city}",
        "hotel_query": f"budget hotels in {req.to_city}",
        "places_query": f"top attractions in {req.to_city}"
    }
    # simulate small delay
    await asyncio.sleep(0.05)
    return {"tasks": tasks}

async def search_agent(tasks: Dict[str, str]) -> Dict[str, Any]:
    METRICS["agent_calls"] += 1
    logger.info("[Search] Running fake searches for tasks")
    # Simulate parallel-ish search results (fake/synthetic)
    await asyncio.sleep(0.12)
    flights = [
        {"airline": "AirFast", "price": random.randint(4000, 12000), "depart": "06:00", "arrive": "09:00"},
        {"airline": "SkyGo", "price": random.randint(4500, 14000), "depart": "12:00", "arrive": "15:00"}
    ]
    hotels = [
        {"name": "Budget Inn", "price_per_night": random.randint(800, 2500), "rating": round(3 + random.random(), 1)},
        {"name": "Comfort Stay", "price_per_night": random.randint(1500, 4000), "rating": round(3 + random.random(), 1)}
    ]
    places = [f"{tasks['places_query']} - {i+1}" for i in range(5)]
    return {"flights": flights, "hotels": hotels, "places": places}

async def budget_agent(search_result: Dict[str, Any], req: PlanRequest) -> Dict[str, Any]:
    METRICS["agent_calls"] += 1
    logger.info("[Budget] Calculating budget")
    days = max(1, req.days)
    cheapest_flight = min((f["price"] for f in search_result["flights"]), default=0)
    cheapest_hotel = min((h["price_per_night"] for h in search_result["hotels"]), default=0)
    food = 400 * days
    transport = 250 * days
    total = cheapest_flight + (cheapest_hotel * days) + food + transport
    status = "within_budget" if total <= req.budget else "over_budget"
    # tiny delay
    await asyncio.sleep(0.02)
    return {"total": total, "status": status, "breakdown": {"flight": cheapest_flight, "hotel_per_night": cheapest_hotel, "food": food, "transport": transport}}

async def summarizer_agent(req: PlanRequest, search_result: Dict[str, Any], budget_result: Dict[str, Any]) -> Dict[str, Any]:
    METRICS["agent_calls"] += 1
    logger.info("[Summarizer] Creating final plan summary")
    plan_id = str(uuid.uuid4())
    itinerary = []
    places = search_result.get("places", [])
    for d in range(req.days):
        itinerary.append(f"Day {d+1}: {places[d % len(places)] if places else 'Local exploration'}")
    await asyncio.sleep(0.01)
    summary = {
        "plan_id": plan_id,
        "from": req.from_city,
        "to": req.to_city,
        "flights": search_result["flights"],
        "hotels": search_result["hotels"],
        "itinerary": itinerary,
        "budget": budget_result
    }
    return summary

# ----------------------------
# Main orchestration endpoint
# ----------------------------
@app.post("/plan")
async def create_plan(req: PlanRequest):
    METRICS["plans_created"] += 1
    # 1) Planner
    planner_res = await planner_agent(req)
    # 2) Search (could be parallel across subqueries; single agent simulates parallel work)
    search_res = await search_agent(planner_res["tasks"])
    # 3) Budget
    budget_res = await budget_agent(search_res, req)
    # 4) Summarize
    summary = await summarizer_agent(req, search_res, budget_res)

    response = {
        "summary": summary,
        "raw": {"planner": planner_res, "search": search_res, "budget": budget_res},
        "metrics": METRICS,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }
    return response

# ----------------------------
# Small health endpoint
# ----------------------------
@app.get("/health")
def health():
    return {"status": "ok", "metrics": METRICS}

# ----------------------------
# __main__ block: support reload by passing module import string
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    import pathlib
    logger.info("Starting Simple Travel Planner on http://127.0.0.1:8000")
    module_name = pathlib.Path(__file__).stem  # filename without .py
    import_string = f"{module_name}:app"
    # Use import string so --reload works when uvicorn restarts child process
    uvicorn.run(import_string, host="127.0.0.1", port=8000, reload=True)
