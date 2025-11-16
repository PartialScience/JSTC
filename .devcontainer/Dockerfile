FROM python:3.12-slim

RUN mkdir -p /workspaces
WORKDIR /workspaces

COPY ./api/requirements.txt /temp/requirements.txt
RUN pip install --no-cache-dir -r /temp/requirements.txt 

CMD ["sleep", "infinity"]   