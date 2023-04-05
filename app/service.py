from io import BytesIO
from typing import List

import requests
from fastapi import FastAPI, Form
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from xhtml2pdf import pisa

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


@app.post("/xhtml2pdf")
async def convert_html_to_pdf(html: str = Form()):
    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)
    filename = "example.pdf"
    response = Response(pdf_buffer.read(), media_type='application/pdf')
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

