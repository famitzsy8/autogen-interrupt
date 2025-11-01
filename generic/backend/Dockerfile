FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./

RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

COPY . .

EXPOSE 8001

CMD ["tail", "-f", "/dev/null"]