FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install streamlit

COPY ./kanbanboard/web .

EXPOSE 8501

# production
# CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
CMD ["tail", "-f", "/dev/null"]