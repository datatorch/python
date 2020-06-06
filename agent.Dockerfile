FROM python:3.8-alpine

RUN pip install datatorch

CMD ["datatorch", "agent"]