from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from strategies.minervini import run_minervini

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("datatables.html", {"request": request})   
    

@router.post("/filter")
async def filter_stocks():
    try:
        df = await run_minervini()
        df = df.replace([float("inf"), float("-inf")], None).fillna(value=0)
        result = df.to_dict(orient="records")
        return JSONResponse(content={"status": "success", "data": result})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)