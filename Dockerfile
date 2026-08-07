FROM python:3.12

WORKDIR /code

RUN mkdir -p /code/db && chown 1018:100 /code/db

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./ /code/app

CMD ["uvicorn", "main:app", "--app-dir", "/code/app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers", "--no-access-log"]

# If running behind a proxy like Nginx or Traefik add --proxy-headers
# CMD ["uvicorn", "main:app", "--app-dir", "/code/app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers", "--no-access-log"]
