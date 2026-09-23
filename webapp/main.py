from flask import Flask, render_template as show_page

app = Flask(__name__)

@app.route('/')
def index():
    return show_page("map.html")
