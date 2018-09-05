#!/usr/bin/env python
from flask import Flask, render_template, request, redirect, jsonify, url_for
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Author, Post
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(open('google.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Writer Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///writerDB.db',
                       connect_args={'check_same_thread': False})
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# Google Connect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code
    code = request.data
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('google.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getAuthorID(data["email"])
    if not user_id:
        user_id = createAuthor(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h3>Welcome, '
    output += login_session['username']
    output += '!</h3>'
    return output


# User Helper Functions
def createAuthor(login_session):
    newAuthor = Author(name=login_session['username'],
                       email=login_session['email'],
                       picture=login_session['picture'])
    session.add(newAuthor)
    session.commit()
    author = session.query(Author).filter_by(
             email=login_session['email']).one()
    return author.id


def getAuthorInfo(author_id):
    author = session.query(Author).filter_by(id=author_id).one()
    return author


def getAuthorID(email):
    try:
        author = session.query(Author).filter_by(email=email).one()
        return author.id
    except:
        return None


# DISCONNECT
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Information
@app.route('/author/<int:author_id>/post/JSON')
def authorPostJSON(author_id):
    author = session.query(Author).filter_by(id=author_id).one()
    posts = session.query(Post).filter_by(author_id=author_id).all()
    return jsonify(Post=[p.serialize for p in posts])


@app.route('/author/<int:author_id>/post/<int:post_id>/JSON')
def postJSON(author_id, post_id):
    post_Item = session.query(Post).filter_by(id=post_id).one()
    return jsonify(post_Item=post_Item.serialize)


@app.route('/author/JSON')
def authorsJSON():
    authors = session.query(Author).all()
    return jsonify(authors=[a.serialize for a in authors])


@app.route('/post/JSON')
def postsJSON():
    posts = session.query(Post).all()
    return jsonify(posts=[p.serialize for p in posts])


# Show Main Page
@app.route('/')
@app.route('/index/')
def showIndex():
    authors = session.query(Author).order_by(asc(Author.name))
    posts = session.query(Post).order_by(desc(Post.id))
    if 'username' not in login_session:
        return render_template('index.html', authors=authors, posts=posts,
                               user_num=0)
    else:
        user_num = session.query(Author).filter_by(
            email=login_session['email']).one()
        return render_template('index.html', authors=authors, posts=posts,
                               user_num=user_num.id)


# Add New Post
@app.route('/author/<int:author_id>/post/new/', methods=['GET', 'POST'])
def newPost(author_id):
    if 'username' not in login_session:
        return redirect('/login')
    author = session.query(Author).filter_by(id=author_id).one()
    if login_session['email'] != author.email:
        return '''<script>function myFunction()
                          {alert('You are not authorized to add post.');}
                  </script>
                  <body onload='myFunction()'>'''
    if request.method == 'POST':
        newItem = Post(title=request.form['title'],
                       description=request.form['description'],
                       author_id=author.id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('showIndex'))
    return render_template('postTool.html', author=author, operation='Add')


# Edit Post
@app.route('/author/<int:author_id>/post/<int:post_id>/edit', methods=['GET', 'POST'])
def editPost(author_id, post_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedPost = session.query(Post).filter_by(id=post_id).one()
    author = session.query(Author).filter_by(id=author_id).one()
    if login_session['email'] != author.email:
        return '''<script>function myFunction()
                          {alert('You are not authorized to edit Post.');}
                  </script>
                  <body onload='myFunction()'>'''
    if request.method == 'POST':
        if request.form['title']:
            editedPost.title = request.form['title']
        if request.form['description']:
            editedPost.description = request.form['description']
        session.add(editedPost)
        session.commit()
        return redirect(url_for('showIndex'))
    return render_template('postTool.html', author_id=author_id,
                           post_id=post_id, item=editedPost, author=author,
                           operation='Edit')


# Delete Post
@app.route('/author/<int:author_id>/post/<int:post_id>/delete', methods=['GET', 'POST'])
def deletePost(author_id, post_id):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Post).filter_by(id=post_id).one()
    author = session.query(Author).filter_by(id=author_id).one()
    if login_session['email'] != author.email:
        return '''<script>function myFunction()
                          {alert('You are not authorized to delete post.');}
                  </script>
                  <body onload='myFunction()'>'''
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('showIndex'))
    else:
        return render_template('postTool.html', item=itemToDelete,
                               operation='Delete', author=author)


# Disconnect
@app.route('/disconnect')
def disconnect():
    gdisconnect()
    del login_session['gplus_id']
    del login_session['access_token']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    return redirect(url_for('showIndex'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
