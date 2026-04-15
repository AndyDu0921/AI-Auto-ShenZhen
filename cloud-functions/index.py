from fastapi import FastAPI
from app.main import app as _app

# EdgeOne Pages Python runtime needs an ASGI-visible FastAPI symbol in this file.
app = _app
