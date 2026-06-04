import asyncio
import os
import sys
import builtins
import json
import threading
import runpy
from datetime import datetime
from glob import glob
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import openpyxl
from concurrent.futures import ThreadPoolExecutor

# Make sure output dir exists
OUTPUT_DIR = os.path.abspath("output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
scraper_thread_executor = ThreadPoolExecutor(max_workers=1)
scraper_future = None
scraper_status = "idle"  # idle | running | done | error
log_queue: asyncio.Queue = asyncio.Queue()
data_queue: asyncio.Queue = asyncio.Queue()
stop_event = threading.Event()
active_scraper_loop = None

class ScrapeRequest(BaseModel):
    city_url: str

class QueueStream:
    def __init__(self, queue, loop):
        self.queue = queue
        self.loop = loop
    
    def write(self, text):
        if text.strip():
            asyncio.run_coroutine_threadsafe(self.queue.put(text.strip()), self.loop)
            # Try to parse as JSON as requested by original instructions
            try:
                data = json.loads(text.strip())
                if isinstance(data, dict) and "name" in data:
                    asyncio.run_coroutine_threadsafe(data_queue.put(data), self.loop)
            except Exception:
                pass
    
    def flush(self):
        pass


def custom_json_dump(obj, fp, *args, **kwargs):
    """
    Monkeypatched json.dump to intercept data when scraper writes output.
    """
    global active_scraper_loop
    if isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict) and "name" in obj[0]:
        if active_scraper_loop:
            for item in obj:
                mapped_item = {
                    "name": item.get("name", "Unknown"),
                    "cuisine": ", ".join(item.get("cuisines", [])) if "cuisines" in item else item.get("cuisine", ""),
                    "rating": str(item.get("ratings", {}).get("dining", {}).get("score", "N/A")) if "ratings" in item else "N/A",
                    "location": item.get("address", item.get("location", "Unknown")),
                    "price": item.get("cost_for_two", item.get("price_for_two", "Unknown")),
                    "contact": item.get("phone", "Unknown")
                }
                asyncio.run_coroutine_threadsafe(data_queue.put(mapped_item), active_scraper_loop)

    return builtins._original_json_dump(obj, fp, *args, **kwargs)

builtins._original_json_dump = json.dump


def custom_open(file, *args, **kwargs):
    """
    Monkeypatched open() to redirect .json outputs to the output/ directory
    """
    if isinstance(file, str) and file.endswith(".json") and os.path.basename(file) == file:
        file = os.path.join(OUTPUT_DIR, file)
    return builtins._original_open(file, *args, **kwargs)

builtins._original_open = builtins.open


def run_scraper_sync(city_url: str, loop: asyncio.AbstractEventLoop):
    global scraper_status, active_scraper_loop
    active_scraper_loop = loop
    
    # Store original builtins
    original_input = builtins.input
    original_stdout = sys.stdout
    
    # Apply monkeypatches
    builtins.input = lambda _="": city_url
    builtins.open = custom_open
    json.dump = custom_json_dump
    sys.stdout = QueueStream(log_queue, loop)
    
    src_path = os.path.abspath("src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    try:
        original_cwd = os.getcwd()
        os.chdir(src_path)
        try:
            runpy.run_module("main", run_name="__main__")
        finally:
            os.chdir(original_cwd)
            
        scraper_status = "done"
        asyncio.run_coroutine_threadsafe(log_queue.put("SCRAPE_COMPLETE"), loop)
        asyncio.run_coroutine_threadsafe(log_queue.put(None), loop)
        asyncio.run_coroutine_threadsafe(data_queue.put(None), loop)
        
    except Exception as e:
        scraper_status = "error"
        asyncio.run_coroutine_threadsafe(log_queue.put(f"ERROR: {str(e)}"), loop)
        asyncio.run_coroutine_threadsafe(log_queue.put(None), loop)
        asyncio.run_coroutine_threadsafe(data_queue.put(None), loop)
    finally:
        # Restore builtins
        builtins.input = original_input
        builtins.open = builtins._original_open
        json.dump = builtins._original_json_dump
        sys.stdout = original_stdout


def convert_json_to_xlsx(output_dir: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_path = os.path.join(output_dir, f"zomato_restaurants_{timestamp}.xlsx")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Restaurants"
    
    # Header
    headers = [
        "Restaurant Name", "Cuisines", "Rating (Dining)", "Rating (Delivery)", 
        "Location", "Address", "Timings", "Cost for Two", "Phone", "Menu Items", "Photos URL"
    ]
    ws.append(headers)
    
    # Find all detailed chunk files
    json_files = glob(os.path.join(output_dir, "scraped_restaurants_from_*_to_*.json"))
    
    for fpath in json_files:
        with builtins._original_open(fpath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for r in data:
                    name = r.get("name", "")
                    cuisines = ", ".join(r.get("cuisines", []))
                    dining_rating = str(r.get("ratings", {}).get("dining", {}).get("score", ""))
                    delivery_rating = str(r.get("ratings", {}).get("delivery", {}).get("score", ""))
                    location = r.get("address", "")
                    address = r.get("address", "")
                    timings = r.get("timing", "")
                    cost = r.get("cost_for_two", "")
                    phone = r.get("phone", "")
                    
                    dishes = []
                    for d in r.get("dishes", []):
                        dish_str = f"{d.get('name', '')} - {d.get('price', '')}"
                        dishes.append(dish_str)
                    menu_items = "; ".join(dishes)
                    
                    photos = "; ".join(r.get("photos", []))
                    
                    ws.append([
                        name, cuisines, dining_rating, delivery_rating,
                        location, address, timings, cost, phone, menu_items, photos
                    ])
            except Exception:
                pass
                
    wb.save(xlsx_path)
    return xlsx_path


@app.post("/scrape")
async def scrape_endpoint(req: ScrapeRequest):
    global scraper_status, scraper_future
    
    if not req.city_url.startswith("https://www.zomato.com"):
        raise HTTPException(status_code=400, detail="Invalid city_url")
        
    if scraper_status == "running":
        raise HTTPException(status_code=400, detail="Scraper already running")
        
    # Clear queues
    while not log_queue.empty():
        await log_queue.get()
    while not data_queue.empty():
        await data_queue.get()
        
    stop_event.clear()
    scraper_status = "running"
    
    loop = asyncio.get_event_loop()
    scraper_future = scraper_thread_executor.submit(run_scraper_sync, req.city_url, loop)
    
    return {"status": "started", "city_url": req.city_url}


@app.post("/stop")
async def stop_endpoint():
    global scraper_status, scraper_future
    
    if scraper_future and scraper_status == "running":
        stop_event.set()
        scraper_future.cancel()
        
    scraper_status = "idle"
    await log_queue.put(None)
    await data_queue.put(None)
    
    return {"status": "stopped"}


@app.get("/download")
async def download_endpoint():
    # check for existing xlsx
    xlsx_files = glob(os.path.join(OUTPUT_DIR, "*.xlsx"))
    if xlsx_files:
        # return the latest one
        latest_file = max(xlsx_files, key=os.path.getmtime)
        return FileResponse(
            path=latest_file,
            filename="zomato_restaurants.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    # if none, scan json chunk files and convert
    json_files = glob(os.path.join(OUTPUT_DIR, "scraped_restaurants_from_*_to_*.json"))
    if json_files:
        xlsx_path = convert_json_to_xlsx(OUTPUT_DIR)
        return FileResponse(
            path=xlsx_path,
            filename="zomato_restaurants.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    raise HTTPException(status_code=404, detail="No output file available yet")


@app.get("/status")
async def status_endpoint():
    return {"status": scraper_status, "queue_size": data_queue.qsize()}


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                item = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                if item is None:
                    break
                await websocket.send_text(item)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/data")
async def ws_data(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                item = await asyncio.wait_for(data_queue.get(), timeout=1.0)
                if item is None:
                    break
                await websocket.send_text(json.dumps(item))
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
