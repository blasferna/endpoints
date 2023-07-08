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
async def create_og_image(title: str, sitename: str):
    fontSize =  '86px' if len(title) < 70 else '62px'
    html = f"""
    <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    background: rgb(248,248,255);
                    background: radial-gradient(circle, rgba(248,248,255,1) 22%, rgba(211,223,255,0.999019676229867) 100%); 
                    color: #080707;
                    height: 100vh;
                    margin: 0;
                    font-family: Arial, sans-serif;
                    padding: 50px;
                }}
            </style>
        </head>
        <body>
            <h1 style="text-align: left; font-size: {fontSize}; max-width: 80%;" >{title}</h1>
            <div style="bottom: 50px; left: 50px; position: absolute; display: flex; align-items:center;">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" style="width: 30px; height: 30px; margin-right: 5px; color: #3574ea;">
                    <path d="M21.721 12.752a9.711 9.711 0 00-.945-5.003 12.754 12.754 0 01-4.339 2.708 18.991 18.991 0 01-.214 4.772 17.165 17.165 0 005.498-2.477zM14.634 15.55a17.324 17.324 0 00.332-4.647c-.952.227-1.945.347-2.966.347-1.021 0-2.014-.12-2.966-.347a17.515 17.515 0 00.332 4.647 17.385 17.385 0 005.268 0zM9.772 17.119a18.963 18.963 0 004.456 0A17.182 17.182 0 0112 21.724a17.18 17.18 0 01-2.228-4.605zM7.777 15.23a18.87 18.87 0 01-.214-4.774 12.753 12.753 0 01-4.34-2.708 9.711 9.711 0 00-.944 5.004 17.165 17.165 0 005.498 2.477zM21.356 14.752a9.765 9.765 0 01-7.478 6.817 18.64 18.64 0 001.988-4.718 18.627 18.627 0 005.49-2.098zM2.644 14.752c1.682.971 3.53 1.688 5.49 2.099a18.64 18.64 0 001.988 4.718 9.765 9.765 0 01-7.478-6.816zM13.878 2.43a9.755 9.755 0 016.116 3.986 11.267 11.267 0 01-3.746 2.504 18.63 18.63 0 00-2.37-6.49zM12 2.276a17.152 17.152 0 012.805 7.121c-.897.23-1.837.353-2.805.353-.968 0-1.908-.122-2.805-.353A17.151 17.151 0 0112 2.276zM10.122 2.43a18.629 18.629 0 00-2.37 6.49 11.266 11.266 0 01-3.746-2.504 9.754 9.754 0 016.116-3.985z" />
                </svg>
                <span style="font-size: 30px; font-weight: 800;">
                {sitename}
                </span>
            </div>
        </body>
    </html>
    """
    options = {
        'format': 'jpeg',
        'width': 1200,
        'height': 630,
        'quality': 100
    }
    image = imgkit.from_string(html, False, options=options)
    return Response(image, media_type="image/jpeg")
