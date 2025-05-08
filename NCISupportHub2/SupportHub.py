from flask import Flask, render_template, abort
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

# Load all available HTML files
def get_available_pages():
    files = os.listdir("templates")
    return [f[:-5] for f in files if f.endswith(".html")]

available_pages = get_available_pages()

@app.route("/")
def index():
    return "<h2>NCI Support Hub (Local)</h2><ul>" + \
        "".join([f'<li><a href="/articles/{page}">{page}</a></li>' for page in available_pages]) + "</ul>"

@app.route("/articles/<slug>")
def article(slug):
    if slug in available_pages:
        return render_template(f"{slug}.html")
    else:
        abort(404)

if __name__ == '__main__':
    print("Support Hub running at http://localhost:5001")
    app.run(port=5001, debug=True)
