FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements-hf.txt .
RUN pip install --no-cache-dir -r requirements-hf.txt

COPY . .

EXPOSE 7860

CMD waitress-serve --host=0.0.0.0 --port=${PORT:-7860} --threads=8 app:app
