from typing import List

import requests
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]
)


@app.get("/get-redirect-url")
async def get(url):
    """Returns the last url if the request is redirected. Useful for frontend use 
    when the input url has CORS protection

    Args:
        url (str): The url try

    Returns:
        str: The redirected url
    """
    r = requests.get(url, timeout=(10, 10))
    return {"url": r.url}
