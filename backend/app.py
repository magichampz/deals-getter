from flask import Flask, jsonify
from flask_ngrok import run_with_ngrok
from web_scraping.scrape import get_webscrape_data

CACHED_DATA = get_webscrape_data()
app = Flask(__name__)
run_with_ngrok(app)

@app.route('/get', methods = ['GET'])
def get_articles():
    return jsonify(CACHED_DATA)

@app.route('/', methods = ['GET'])
def default_test():
    return "Hello world"
if __name__ == "__main__":
    app.run(debug=True)