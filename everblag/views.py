import datetime
import os

from evernote.api.client import EvernoteClient
import evernote.edam.type.ttypes as types
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.notestore.NoteStore as NoteStore
from flask import redirect, render_template, request, session, flash
from sqlalchemy.orm.exc import NoResultFound

from everblag import app, db, cache
from everblag.models import User, Theme
from everblag.util import slugify, strip_ml_tags


def get_evernote_client(token=None):
    sandbox = True if os.getenv('EN_USE_SANDBOX') else False

    if token:
        return EvernoteClient(token=token, sandbox=sandbox)
    else:
        return EvernoteClient(
            consumer_key=os.environ['EN_CONSUMER_KEY'],
            consumer_secret=os.environ['EN_CONSUMER_SECRET'],
            sandbox=sandbox)


def initialize_evernote_account(client):
    """
    Returns the guid of the 'blog' notebook, creates it if it doesn't exist.
    """
    note_store = client.get_note_store()
    notebooks = note_store.listNotebooks()

    # Create a blog if the user doesn't have one.
    blog = None

    for nb in notebooks:
        if nb.name == 'blog':
            blog = nb

    if not blog:
        blog = note_store.createNotebook(client.token, types.Notebook(name='blog'))

    return blog.guid


def find_blog_owner(blog_slug):
    try:
        user = db.session.query(User).\
            filter(User.blog_slug == blog_slug).one()
    except NoResultFound:
        return None

    return user


def create_user(evernote_token, blog_name, theme_id):
    guid = initialize_evernote_account(
        get_evernote_client(token=evernote_token))

    user = User(evernote_token, blog_name, guid, theme_id)

    db.session.add(user)
    db.session.commit()

    return user


@app.route('/')
def index():
    """ The Everblag page, promotes Everblag, sign up, etc. """

    if session.get('signed-up'):
        user = db.session.query(User).\
            filter(User.id == session.get('uid')).one()
        session['signed-up'] = None

        return render_template('index.html', success=True,
                               blog_slug=user.blog_slug)

    return render_template('index.html', success=False)


@app.route('/start-auth', methods=['POST'])
def start_auth():
    client = get_evernote_client()
    callback_url = 'http://%s%s' % (request.host, '/sign-up')
    request_token = client.get_request_token(callback_url)

    # These tokens will be used to get the final access token.
    session['oauth_token'] = request_token['oauth_token']
    session['oauth_token_secret'] = request_token['oauth_token_secret']

    return redirect(client.get_authorize_url(request_token))


@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    """
    Hit this once the user has authenticated the request token with evernote.
    Give then a view to add additional information to their account. On post,
    add shit to the database.
    """

    if request.method == 'POST':
        if not session.get('access_token'):
            return redirect('/')

        blog_name = request.form.get('blog-name')
        theme_name = request.form.get('theme-name')

        try:
            theme = db.session.query(Theme).\
                filter(Theme.name == theme_name).one()
        except: # I KNOW ITS BAD DGAF.
            return redirect('/')

        if not blog_name or len(blog_name) < 5 or len(blog_name) > 64:
            return redirect('/')

        user = create_user(session['access_token'], blog_name, theme.id)

        session['signed-up'] = 'True'
        session['uid'] = user.id

        return redirect('/')

    try:
        client = get_evernote_client()
        client.get_access_token(
            session['oauth_token'],
            session['oauth_token_secret'],
            request.args.get('oauth_verifier', ''))
    except:
        return redirect('/')

    session['access_token'] = client.token

    themes = db.session.query(Theme).all()

    return render_template(
        '/sign-up.html', themes=themes)


@app.route('/f/<blog_slug>')
def blog_index(blog_slug):
    """
    The archive or main page for a user's blog.

    This function triggers a cache check vs evernote.
    """

    blog_slug = str(blog_slug)

    c = cache.get(blog_slug)

    if c:
        return c

    user = find_blog_owner(blog_slug)

    if not user:
        return "Not a user"

    client = get_evernote_client(user.evernote_token)

    note_store = client.get_note_store()

    note_list = note_store.findNotes(
        user.evernote_token, NoteStore.NoteFilter(
            notebookGuid=user.blog_guid, ascending=False),
        0, 25)

    note_list.notes = sorted(note_list.notes, key=lambda p: -p.created)

    posts = []

    for note in note_list.notes:
        posts.append({
            'title': note.title,
            'slug': slugify(note.title),
            'date': datetime.date.fromtimestamp(note.updated/1000)
            })

    html = render_template('/archive.html', posts=posts,
                           title=user.blog_name, blog_slug=blog_slug,
                           stylesheet=user.theme.static_path)

    cache.set(blog_slug, html, time=app.cache_tte)

    return html


def note_guid_from_slug(note_store, user, slug):
    note_list = note_store.findNotes(
        user.evernote_token, NoteStore.NoteFilter(
            notebookGuid=user.blog_guid, ascending=True),
        0, 200)

    for post in note_list.notes:
        if slug == slugify(post.title):
            return post.guid

    return None


@app.route('/f/<blog_slug>/<post_slug>')
def blog_post(blog_slug, post_slug):
    """
    A blog post page. This page triggers a search on evernote to see
    if the cache is outdated.
    """

    cache_key = str("%s/%s" % (blog_slug, post_slug))

    c = cache.get(cache_key)

    if c:
        return c

    user = find_blog_owner(blog_slug)

    client = get_evernote_client(user.evernote_token)

    note_store = client.get_note_store()

    guid = note_guid_from_slug(note_store, user, post_slug)

    note = note_store.getNote(user.evernote_token, guid, True, False, False, False)

    html = render_template(
        'post.html', title=note.title, content=note.content,
        date=datetime.date.fromtimestamp(note.updated/1000),
        stylesheet=user.theme.static_path)

    cache.set(cache_key, html, time=app.cache_tte)

    return html
