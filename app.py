from flask import Flask, flash, json, redirect, render_template, session, url_for, request, jsonify
from forms.login import LoginForm
from forms.signup import SignupForm
import mysql.connector
from mysql.connector import Error
import re
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

mysql_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'ashram_local',
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
        return render_template('home_loggedin.html', username=session['username'])
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
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if account and bcrypt.check_password_hash(account['password'], password):
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
        email = form.email.data
        username = form.username.data
        password = form.password.data
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        # Insert into the users table

        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Check if the username or email already exists
            cursor.execute("SELECT * FROM users WHERE email=%s OR username=%s", (email, username))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Email or Username already exists. Please choose another.', 'danger')
            else:
                # Insert new user into the table
                cursor.execute("INSERT INTO users (email, username, password) VALUES (%s, %s, %s)", (email, username, hashed_password))
                connection.commit()
                flash('You have successfully signed up!', 'success')
                return redirect(url_for('login'))  # Assuming you have a login route
        connection.close()

    return render_template('signup.html', form=form)

@app.route('/logout')
def logout():
    session.clear()  # Clears all session data
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

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
