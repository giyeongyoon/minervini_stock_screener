from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from app.routes import filter

app = FastAPI()
app.include_router(filter.router)

templates = Jinja2Templates(directory="app/templates")
