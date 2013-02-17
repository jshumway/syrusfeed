import os

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

app.debug = True if os.getenv('DEBUG') else False

app.secret_key = os.environ['SECRET_KEY']

import everblag.filters

app.jinja_env.filters.update(everblag.filters.export_filters())

import views
import api


def run():
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# STFU pyflakes!
__all__ = ['views', 'api']
