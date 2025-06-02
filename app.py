from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from main import main as minervini_filtering

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("datatables.html", {"request": request})   
    

@app.post("/filter")
async def filter_stocks():
    try:
        df = await minervini_filtering()
        df = df.replace([float("inf"), float("-inf")], None).fillna(value=0)
        result = df.to_dict(orient="records")
        return JSONResponse(content={"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
    