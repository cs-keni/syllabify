# Flask entry point.
# TODO: Create Flask app, load config (core.config), register blueprints for api.auth,
#       api.syllabus, api.schedule, api.export. Run with FLASK_APP=app.main.

from flask import Flask
import mysql.connector
import os

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host = "mysql",
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        database = os.getenv("DB_NAME")
    )

@app.route("/")
def index():
    return"sample index text"

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000)