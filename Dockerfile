FROM python:latest

WORKDIR /src

ENV PYTHONWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt 

COPY ./src ./src

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]