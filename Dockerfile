FROM python:3.10-alpine
WORKDIR /code
COPY . /code

# RUN pip install --no-cache-dir --prefer-binary shapely

RUN pip3 install -r requirements.txt
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${FINANCE_PORT}"]
