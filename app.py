import logging
import string
import traceback
import random
import sqlite3
from datetime import datetime
from flask import * # Flask, g, redirect, render_template, request, url_for
from functools import wraps

app = Flask(__name__)

# These should make it so your Flask app always returns the latest version of
# your HTML, CSS, and JS files. We would remove them from a production deploy,
# but don't change them here.
app.debug = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache"
    return response


def get_db():
    db = getattr(g, '_database', None)

    if db is None:
        db = g._database = sqlite3.connect('db/watchparty.sqlite3')
        db.row_factory = sqlite3.Row
        setattr(g, '_database', db)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    db = get_db()
    cursor = db.execute(query, args)
    print("query_db")
    print(cursor)
    rows = cursor.fetchall()
    print(rows)
    db.commit()
    cursor.close()
    if rows:
        if one: 
            return rows[0]
        return rows
    return None


def new_user():
    name = "Unnamed User #" + ''.join(random.choices(string.digits, k=6))
    password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    api_key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=40))
    u = query_db('insert into users (name, password, api_key) ' + 
        'values (?, ?, ?) returning id, name, password, api_key',
        (name, password, api_key),
        one=True)
    return u


def get_user_from_cookie(request):
    user_id = request.cookies.get('user_id')
    password = request.cookies.get('user_password')
    if user_id and password:
        return query_db('select * from users where id = ? and password = ?', [user_id, password], one=True)
    return None


def render_with_error_handling(template, **kwargs):
    try:
        return render_template(template, **kwargs)
    except:
        t = traceback.format_exc()
        return render_template('error.html', args={"trace": t}), 500

# ------------------------------ NORMAL PAGE ROUTES ----------------------------------

@app.route('/')
def index():
    print("index") # For debugging
    user = get_user_from_cookie(request)

    if user:
        rooms = query_db('select * from rooms')
        return render_with_error_handling('index.html', user=user, rooms=rooms)
    
    return render_with_error_handling('index.html', user=None, rooms=None)

@app.route('/rooms/new', methods=['GET', 'POST'])
def create_room():
    print("create room") # For debugging
    user = get_user_from_cookie(request)
    if user is None: return {}, 403

    if (request.method == 'POST'):
        name = "Unnamed Room " + ''.join(random.choices(string.digits, k=6))
        room = query_db('insert into rooms (name) values (?) returning id', [name], one=True)            
        return redirect(f'{room["id"]}')
    else:
        return app.send_static_file('create_room.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    print("signup")
    user = get_user_from_cookie(request)

    if user:
        return redirect('/profile')
        # return render_with_error_handling('profile.html', user=user) # redirect('/')
    
    if request.method == 'POST':
        u = new_user()
        print("u")
        print(u)
        for key in u.keys():
            print(f'{key}: {u[key]}')

        resp = redirect('/profile')
        resp.set_cookie('user_id', str(u['id']))
        resp.set_cookie('user_password', u['password'])
        return resp
    
    return redirect('/login')

@app.route('/profile')
def profile():
    print("profile")
    user = get_user_from_cookie(request)
    if user:
        return render_with_error_handling('profile.html', user=user)
    
    redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    print("login")
    user = get_user_from_cookie(request)

    if user:
        return redirect('/')
    
    if request.method == 'POST':
        name = request.form['username']
        print(name)
        password = request.form['password']
        print(password)
        u = query_db('select * from users where name = ? and password = ?', [name, password], one=True)
        if user:
            print("hello")
            resp = make_response(redirect("/"))
            resp.set_cookie('user_id', u.id)
            resp.set_cookie('user_password', u.password)
            return resp

    return render_with_error_handling('login.html', failed=True)   

@app.route('/logout')
def logout():
    resp = make_response(redirect('/'))
    resp.set_cookie('user_id', '')
    resp.set_cookie('user_password', '')
    return resp

@app.route('/rooms/<int:room_id>')
def room(room_id):
    user = get_user_from_cookie(request)
    if user is None: return redirect('/')

    room = query_db('select * from rooms where id = ?', [room_id], one=True)
    return render_with_error_handling('room.html',
            room=room, user=user)

# -------------------------------- API ROUTES ----------------------------------
def validate_api_key(user_id, api_key):
    db = get_db()
    user = db.execute('SELECT api_key FROM users WHERE id = ?', [user_id]).fetchone()
    return user and user['api_key'] == api_key


# GET to get all the messages in a room
@app.route('/api/rooms/<int:room_id>/messages', methods=['GET'])
def get_room_messages(room_id):
    api_key = request.headers.get('X-Api-Key')
    user_id = request.headers.get('User-ID')

    if not api_key or not user_id or not validate_api_key(user_id, api_key):
        abort(403, description="Invalid or missing API Key")

    messages = query_db(
        'SELECT u.name, m.body, m.id FROM messages m LEFT JOIN users u ON m.user_id = u.id WHERE room_id = ?',
        [room_id])
    return jsonify([dict(msg) for msg in messages])


# POST to post a new message to a room
@app.route('/api/rooms/<int:room_id>/messages', methods=['POST'])
def post_message(room_id):
    api_key = request.headers.get('X-Api-Key')
    user_id = request.headers.get('User-ID')

    if not api_key or not user_id or not validate_api_key(user_id, api_key):
        abort(403, description="Invalid or missing API Key")

    body = request.args.get('comment')
    try:
        query = 'INSERT INTO messages (user_id, room_id, body) VALUES (?, ?, ?)'
        args = (user_id, room_id, body)
        db = get_db()
        db.execute(query, args)
        db.commit()
        return jsonify({'success': 'Message posted'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# POST to change the user's name
@app.route('/api/user/name', methods=['POST'])
def update_username():
    api_key = request.headers.get('X-Api-Key')
    user_id = request.headers.get('User-ID')
    new_username = request.json.get('newUsername')

    if not api_key or not new_username or not user_id or not validate_api_key(user_id, api_key):
        return jsonify({'error': 'Unauthorized or Missing Data'}), 403

    try:
        db = get_db()
        db.execute('UPDATE users SET name = ? WHERE id = ?', [new_username, user_id])
        db.commit()
        return jsonify({'success': 'Username updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/password', methods=['POST'])
def update_password():
    api_key = request.headers.get('X-Api-Key')
    user_id = request.headers.get('User-ID')
    new_password = request.json.get('newPassword')

    if not api_key or not new_password or not user_id or not validate_api_key(user_id, api_key):
        return jsonify({'error': 'Unauthorized or Missing Data'}), 403

    try:
        db = get_db()
        db.execute('UPDATE users SET password = ? WHERE id = ?', [new_password, user_id])
        db.commit()
        return jsonify({'success': 'Password updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# POST to change the name of a room
@app.route('/api/rooms/<int:room_id>', methods=['POST'])
def update_room_name(room_id):
    api_key = request.headers.get('X-Api-Key')
    user_id = request.headers.get('User-ID')
    new_name = request.json.get('name')

    if not api_key or not new_name or not user_id or not validate_api_key(user_id, api_key):
        return jsonify({'error': 'Unauthorized or Missing Data'}), 403

    try:
        db = get_db()
        db.execute('UPDATE rooms SET name = ? WHERE id = ?', [new_name, room_id])
        db.commit()
        return jsonify({'success': 'Room name updated', 'name': new_name}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500






