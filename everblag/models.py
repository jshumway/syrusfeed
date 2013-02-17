from datetime import datetime
import re

from sqlalchemy import Column, Integer, String, DateTime

from everblag import db
from everblag.util import slugify


class User(db.Model):
    """ A user. """

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False, unique=True)

    evernote_token = Column(String, nullable=False, unique=True)
    token_auth_date = Column(DateTime, default=datetime.utcnow,
                             nullable=False)

    join_date = Column(DateTime, default=datetime.utcnow,
                       nullable=False)
    blog_name = Column(String, nullable=False)
    blog_slug = Column(String, nullable=False, unique=True)
    blog_guid = Column(String, nullable=False, unique=True)

    # This should be an id foreignKey
    theme_name = Column(String, nullable=False)

    def __init__(self, evernote_token, blog_name, blog_guid, theme_name):
        self.evernote_token = evernote_token
        self.blog_name = blog_name
        self.blog_slug = slugify(blog_name)
        self.blog_guid = blog_guid
        self.theme_name = theme_name

        self.name = re.search('A=([\d\w]+):H=', self.evernote_token).group(1)

    def __repr__(self):
        return "<User('%s', '%s', '%s')>" % (
            self.id, self.blog_name, self.theme_name)
