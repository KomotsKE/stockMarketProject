FROM python:latest

WORKDIR /app

ENV PYTHONWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

COPY ./requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt 

COPY ./src ./src
COPY ./entrypoint.sh ./entrypoint.sh
COPY ./alembic.ini ./alembic.ini
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]