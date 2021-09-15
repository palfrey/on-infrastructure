import os

from flask import Flask, render_template

app = Flask(__name__)

names = {
    "longhorn": "Longhorn",
    "flower": "Flower",
    "rabbitmq": "RabbitMQ",
    "grafana": "Grafana",
}


@app.route("/")
def index():
    root = os.environ.get("URL_ROOT", "")
    protocol = os.environ.get("URL_PROTOCOL", "")
    return render_template("index.html", root=root, protocol=protocol, names=names)
