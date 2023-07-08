FROM python:3.8

RUN apt-get install -y wkhtmltopdf

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
COPY ./wsgi-service.py /code/wsgi-service.py 

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["uvicorn", "wsgi-service:app", "--host", "0.0.0.0", "--port", "80"]
