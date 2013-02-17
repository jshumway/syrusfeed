import os

import pylibmc
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy


app = Flask(__name__, static_url_path=os.getenv('STATIC_PATH', '/static'))

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

# The memcache instance.
if os.getenv('USE_SIMPLE_MEMCACHE'):
    cache = pylibmc.Client(servers=['127.0.0.1'], binary=True)
else:
    cache = pylibmc.Client(
        servers = [os.getenv('MEMCACHE_SERVERS')],
        username = os.getenv('MEMCACHE_USERNAME'),
        password = os.getenv('MEMCACHE_PASSWORD'),
        binary=True)

app.cache_tte = int(os.getenv('MEMCACHE_GLOBAL_TTE', 5*60))

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
