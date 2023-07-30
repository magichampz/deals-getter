from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

@app.route('/get', methods = ['GET'])
def get_articles():
    return jsonify({"Hello":"world"})


if __name__ == "__main__":
    app.run(debug=True)