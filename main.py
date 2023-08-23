import re
import requests
from bs4 import BeautifulSoup
import time
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sites.db'
db = SQLAlchemy(app)


class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), unique=True)
    indexed = db.Column(db.Boolean, default=False)
    server_code = db.Column(db.Integer)

    def __repr__(self):
        return f"Site(id={self.id}, url='{self.url}', indexed={self.indexed}, server_code={self.server_code})"


@app.before_first_request
def create_tables():
    db.create_all()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        urls = request.form.get('urls').split('\n')
        for url in urls:
            url = url.strip()
            if not url:
                continue

            site = Site.query.filter_by(url=url).first()
            if site is None:
                site = Site(url=url)
                db.session.add(site)
                db.session.commit()

            process_site(site)

        # Odświeżanie danych po dodaniu nowych adresów URL
        sites = Site.query.all()
        return render_template('index.html', sites=sites)
    else:
        sites = Site.query.all()
        return render_template('index.html', sites=sites)


@app.route('/clear-database', methods=['GET', 'POST'])
def clear_records_db():
    Site.query.delete()
    db.session.commit()
    sites = Site.query.all()
    return render_template('index.html', sites=sites)


def process_site(site):
    try:
        google_url = f"https://www.google.com/search?q=site:{site.url}&hl=en"
        response = requests.get(google_url, cookies={"CONSENT": "YES+1"})
        soup = BeautifulSoup(response.content, "html.parser")
        not_indexed = re.compile("did not match any documents")

        if soup(text=not_indexed):
            site.indexed = False
        else:
            site.indexed = True

        site.server_code = response.status_code
        db.session.commit()
    except requests.exceptions.RequestException:
        pass  # Handle connection errors


@app.route('/rescan/<int:site_id>', methods=['POST'])
def rescan(site_id):
    site = Site.query.get(site_id)
    if site:
        site.indexed = False
        site.server_code = None
        db.session.commit()
        process_site(site)
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
