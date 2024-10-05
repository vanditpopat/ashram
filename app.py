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

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch the current user's information from the database
    cursor.execute('SELECT email, username FROM users WHERE id = %s', (session['id'],))
    user_info = cursor.fetchone()

    # Handle the POST request to update the user's info
    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']

        if new_username:
            cursor.execute('UPDATE users SET username = %s WHERE id = %s', (new_username, session['id']))
        
        if new_password:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_password, session['id']))

        connection.commit()
        flash('Your profile has been updated!', 'success')

    cursor.close()
    connection.close()

    return render_template('profile.html', user=user_info)

@app.route('/webview')
def show_categories():
    if 'loggedin' not in session:
        flash('Please log in to view the categories.', 'warning')
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT wc.id, wc.categoryname AS category, COUNT(p.webcatid) AS count
        FROM WebCategories wc
        LEFT JOIN Pravachans p ON wc.id = p.webcatid
        GROUP BY wc.id, wc.categoryname
        ORDER BY wc.id
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    cursor.close()
    connection.close()

    return render_template('categories.html', categories=results)

@app.route('/category/<category_id>')
def category_page(category_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT id, title FROM Pravachans WHERE webcatid = %s
    """
    cursor.execute(query, (category_id,))
    pravachans = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('category_page.html', pravachans=pravachans)
 
@app.route('/pravachan/<pravachan_id>')
def pravachan_page(pravachan_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT * FROM Pravachans WHERE id = %s
    """
    cursor.execute(query, (pravachan_id,))
    pravachan = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template('pravachan_details.html', pravachan=pravachan)

@app.route('/satsangs')
def index_counts():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # SQL query to get the count of each letter prefix
    query = """
        SELECT SUBSTRING(id, 1, 1) AS id_prefix, COUNT(*) AS count
        FROM pravachans
        GROUP BY id_prefix
        ORDER BY id_prefix;
    """
    cursor.execute(query)
    index_counts = cursor.fetchall()

    cursor.close()
    connection.close()

    # Split the data into two columns for the table layout
    half = len(index_counts) // 2
    first_column_data = index_counts[:half]
    second_column_data = index_counts[half:]

    return render_template('satsang.html', first_column_data=first_column_data, second_column_data=second_column_data)

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
