FROM python:3.7-alpine
RUN pip install flask
WORKDIR /app
COPY app.py /app
RUN mkdir /app/templates
COPY templates/index.html /app/templates
EXPOSE 5000
CMD python -m flask run --host=0.0.0.0
