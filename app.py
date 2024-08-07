from flask import Flask, flash, json, redirect, render_template, session, url_for, request, jsonify
from forms.login import LoginForm
from forms.signup import SignupForm
import mysql.connector
from mysql.connector import Error
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

mysql_config = {
    'host': '198.100.45.83',
    'user': 'nilesh',
    'password': 'GuruDeva~13',
    'database': 'ashram',
    'port': 3306
}

def get_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**mysql_config)
    except Error as e:
        print(f"Error: '{e}'")
    return connection

@app.route('/')
def home():
    if 'loggedin' in session:
        return render_template('home_loggedin.html')
    else:
        return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        cursor.close()
        connection.close()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for('home'))
        else:
            flash('Incorrect username/password!')
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            flash('Account already exists!')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash('Please fill out the form!')
        else:
            cursor.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)', (username, password, email,))
            connection.commit()
            flash('You have successfully registered!')
            return redirect(url_for('login'))
        cursor.close()
        connection.close()
    return render_template('signup.html', form=form)

@app.route('/webview')
def webview():
    data = [
        {'sr_no': 1, 'category': 'Books', 'link': 'https://example.com/books'},
        {'sr_no': 2, 'category': 'Articles', 'link': 'https://example.com/articles'},
        {'sr_no': 3, 'category': 'Videos', 'link': 'https://example.com/videos'}
    ]
    return render_template('web_view.html', data=data)

@app.route('/email')
def emaillookup():
    return render_template('lookup.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:
        return jsonify([])
    suggestions = []
    with open('data.json', 'r') as file:
        data = json.load(file)
        suggestions = [word for word in data if word.lower().startswith(query.lower())]
    return jsonify(suggestions)

@app.route('/select', methods=['POST'])
def select_name():
    name = request.json['name']
    with open('data.json', 'r') as file:
        data = json.load(file)
    if name in data:
        data.remove(name)
        with open('data.json', 'w') as file:
            json.dump(data, file)
    return jsonify({'success': True})

@app.route('/deselect', methods=['POST'])
def deselect_name():
    name = request.json['name']
    with open('data.json', 'r+') as file:
        data = json.load(file)
    if name not in data:
        data.append(name)
        data.sort()  # Optional: Sort the list if required
        with open('data.json', 'w') as file:
            json.dump(data, file)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
