FROM python:3.12-slim

WORKDIR /app

RUN pip install pipenv

COPY data/arsonor_chunks_300_50.json data/arsonor_chunks_300_50.json
COPY ["Pipfile", "Pipfile.lock", "./"]

RUN pipenv install --deploy --ignore-pipfile --system

COPY arsonor_assistant .

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]