FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend-admin/app ./app
COPY frontend-admin/static ./static
COPY frontend-admin/templates ./templates

EXPOSE 7800

CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "7800", "--reload"]
