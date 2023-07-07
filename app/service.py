import json
from functools import wraps
from io import BytesIO
from typing import List, Union

import imgkit
import requests
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from gtts import gTTS, gTTSError
from gtts.lang import tts_langs
from pydantic import BaseModel, BaseSettings
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from xhtml2pdf import pisa


class Settings(BaseSettings):
    NOTION_API_KEY: str = ""
    NOTION_VOCABULARY_DATABASE_ID: str = ""

    class Config:
        env_file = ".env"


class Vocabulary(BaseModel):
    text: str
    example: Union[str, None] = None
    audios: List[dict] = []


class VocabularyResponse(BaseModel):
    object: str = "list"
    results: List[Vocabulary] = []
    next_cursor: Union[str, None] = None
    has_more: bool = False


settings = Settings()
app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]
)
tts_langs = tts_langs()


def verify_lang(func):
    @wraps(func)
    def replace_func(text, lang="en"):
        if lang not in tts_langs:
            raise HTTPException(
                detail=f"{lang} is not a valid language code.", status_code=400
            )

        return func(text, lang)

    return replace_func


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
    response = Response(pdf_buffer.read(), media_type="application/pdf")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.get("/vocabulary")
async def vocabulary(status: str = "") -> VocabularyResponse:
    database_id = settings.NOTION_VOCABULARY_DATABASE_ID
    url = f"https://api.notion.com/v1/databases/{database_id}/query"

    payload = {
        "filter": {
            "property": "Status",
            "multi_select": {"contains": status},
        }
    }

    headers = {
        "Authorization": f"Bearer {settings.NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2021-08-16",
    }

    response = requests.request(
        "POST", url, data=json.dumps(payload), headers=headers
    ).json()

    results = []

    vr = VocabularyResponse()
    vr.object = response.get("object", "list")

    for result in response.get("results", []):
        properties = result.get("properties")
        text = properties["Vocabulary"]["title"][0]["plain_text"]

        example = properties["Example"]["rich_text"]
        if len(example) > 0:
            example = example[0]["plain_text"]
        else:
            example = ""

        audios = []
        for sound in properties["Example Sound"].get("files", []):
            audios.append({"name": sound["name"], "url": sound["file"]["url"]})

        results.append(Vocabulary(text=text, example=example, audios=audios))

    vr.results = results
    vr.next_cursor = response.get("next_cursor")
    vr.has_more = response.get("has_more")

    return vr


@verify_lang
@app.get("/tts")
async def tts(text, lang="en"):
    mp3 = BytesIO()
    try:
        gTTS(text=text, lang=lang).write_to_fp(mp3)
    except (AssertionError, ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    except gTTSError as e:
        if e.rsp is not None:
            headers = e.rsp.headers
            headers.pop("Content-Length", None)

            raise HTTPException(
                status_code=e.rsp.status_code,
                detail=e.rsp.content.decode(),
                headers=headers,
            )

        raise

    mp3.seek(0)
    return StreamingResponse(mp3, media_type="audio/mp3")


@app.get("/og-image")
async def create_og_image(title: str):
    fontSize =  '96px' if len(title) < 60 else '72px'
    html = f"""
    <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    background: #d3d9fd;
                    color: #000100;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    font-family: Arial, sans-serif;
                }}
            </style>
        </head>
        <body>
            <h1 style="max-width: 300px">{title}</h1>
        </body>
    </html>
    """
    options = {
        'format': 'jpeg',
        'width': 600,
        'height': 315,
        'quality': 100
    }
    imgkit.from_string(html, 'out.jpg', options=options)
    return FileResponse('out.jpg', media_type='image/jpeg')
