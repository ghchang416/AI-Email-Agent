FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install uv
RUN uv pip install -r requirements.txt --system

COPY ./kanbanboard/server .

# production
# CMD ["python", "main.py"]
CMD ["tail", "-f", "/dev/null"]