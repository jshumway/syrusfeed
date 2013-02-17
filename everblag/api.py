from flask import request
from sqlalchemy.exc import IntegrityError

from everblag import app, db
from everblag.models import User
from everblag.views import create_user
from everblag.util import slugify


@app.route('/api/users/name-available', methods=['GET'])
def is_username_available():
    uname = request.args['uname']

    if db.session.query(User).filter(User.name == uname).count() > 0:
        return 'false'

    return 'true'


@app.route('/api/feeds/name-available', methods=['GET'])
def is_feedname_available():
    fname = request.args['fname']

    fslug = slugify(fname)

    if db.session.query(User).filter(User.blog_slug == fslug).count() > 0:
        return 'false'

    return 'true'


@app.route('/api/users', methods=['POST'])
def post_user():
    try:
        blog_name = request.form['blog-name']
        theme_selection = request.form['theme-name']
        evernote_token = request.form['evernote-token']
    except KeyError:
        return "Error: missing required arguments."

    try:
        create_user(evernote_token, blog_name, theme_selection)
    except IntegrityError:
        return "Error: blog name or username wasn't unique."

    return 'success'
