import logging
from datetime import timedelta, date

from flask import Flask, request, jsonify
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger('API')
handler = logging.StreamHandler()
formatter = logging.Formatter(fmt='%(asctime)s | <%(name)s> | %(message)s', datefmt='%H:%M:%S %d.%m.%Y')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:postgres@postgres/for_metro'

manager = Manager(app)
db = SQLAlchemy(app)


def to_date(date):
    return date.strftime("%d.%m.%Y")


class News(db.Model):
    __tablename__ = 'news'

    id = db.Column(db.Integer(), unique=True, primary_key=True, autoincrement=True)
    news_id = db.Column(db.Integer(), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    url_image = db.Column(db.String(120), nullable=False)
    news_date = db.Column(db.Date(), nullable=False)
    parsed_date = db.Column(db.DateTime(), nullable=False)

    @property
    def serialize(self):
        return {
            'title': self.title,
            'url_image': self.url_image,
            'publish_date': to_date(self.news_date),
        }

    def __repr__(self):
        return f'<News "{self.title}">'


@app.route('/metro/news')
def home():
    days_count = request.args.get('day')
    if days_count:
        start = date.today()
        end = start - timedelta(days=int(days_count))
        result = News.query.filter(News.news_date >= end).order_by(News.news_date.desc())
        if result.count() == 0:
            return jsonify({"message": "No data"})
        return jsonify([i.serialize for i in result.all()])

    return jsonify({"warning": 'The <<day>> argument was not passed'})


@app.errorhandler(Exception)
def handle_exception(e: Exception):
    return jsonify({"error": str(e)})


if __name__ == '__main__':
    manager.run()
