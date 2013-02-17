import datetime
import os

from evernote.api.client import EvernoteClient
import evernote.edam.type.ttypes as types
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.notestore.NoteStore as NoteStore
from flask import redirect, render_template, request, session
from sqlalchemy.orm.exc import NoResultFound

from everblag import app, db
from everblag.models import User
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


def create_user(evernote_token, blog_name, theme_name):
    guid = initialize_evernote_account(
        get_evernote_client(token=evernote_token))

    user = User(evernote_token, blog_name, guid, 'default')

    db.session.add(user)
    db.session.commit()


@app.route('/')
def index():
    """ The Everblag page, promotes Everblag, sign up, etc. """

    return render_template('index.html')


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

        if not blog_name or len(blog_name) < 5 or len(blog_name) > 64:
            return redirect('/')

        create_user(session['access_token'], blog_name, 'default')

        return "Success!"

    try:
        client = get_evernote_client()
        client.get_access_token(
            session['oauth_token'],
            session['oauth_token_secret'],
            request.args.get('oauth_verifier', ''))
    except:
        return redirect('/')

    session['access_token'] = client.token

    return render_template('/sign-up.html')


@app.route('/f/<blog_slug>')
def blog_index(blog_slug):
    """
    The archive or main page for a user's blog.

    This function triggers a cache check vs evernote.
    """

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

    return render_template('/archive.html', posts=posts,
                           title=user.blog_name, blog_slug=blog_slug)


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

    user = find_blog_owner(blog_slug)

    client = get_evernote_client(user.evernote_token)

    note_store = client.get_note_store()

    guid = note_guid_from_slug(note_store, user, post_slug)

    note = note_store.getNote(user.evernote_token, guid, True, False, False, False)

    return render_template(
        'post.html', title=note.title, content=note.content,
        date=datetime.date.fromtimestamp(note.updated/1000))