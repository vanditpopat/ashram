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
    error_message = None  # Initialize error message
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
            flash('You have viewers privileges. For more privileges, contact the ashram.', 'info')
            print("Loggedin")
            return redirect(url_for('home'))
        else:
            error_message = 'Incorrect username or password!'  # Set the error message for invalid login
    
    return render_template('login.html', form=form, error_message=error_message)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        try:
            # Establish a connection to the database
            connection = get_db_connection()
            
            with connection.cursor(dictionary=True) as cursor:
                # Check if the username or email already exists
                cursor.execute("SELECT * FROM users WHERE email=%s OR username=%s", (email, username))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    # If an existing user is found, flash a message and prevent signup
                    flash('Email or Username already exists. Please choose another.', 'danger')
                else:
                    # Insert the new user into the users table
                    cursor.execute("INSERT INTO users (email, username, password) VALUES (%s, %s, %s)", (email, username, hashed_password))
                    connection.commit()
                    
                    # Automatically log the user in after signup
                    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    account = cursor.fetchone()
                    
                    if account:
                        # Set session variables to log the user in
                        session['loggedin'] = True
                        session['id'] = account['id']
                        session['username'] = account['username']

                        flash('You have successfully signed up and are logged in!', 'success')
                        flash('You have viewers privileges. For more privileges, contact the ashram.', 'info')

                        return redirect(url_for('home'))
                    else:
                        flash('Error occurred while logging in after signup. Please try again.', 'danger')
            
        except Error as e:
            # Print the error message for debugging
            print(f"Database error: {e}")
            flash('An error occurred while signing up. Please try again later.', 'danger')
        
        finally:
            # Ensure the database connection is closed properly
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

@app.route('/retreat')
def view_retreats():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    query = """
    SELECT 
    p.title AS pravachan_title,
    p.id AS pravachan_id,
    p.date,
    p.hour,
    p.webseq,
    p.retreatNumber,
    r.retreatTitle AS retreat_title,
    r.retreatTotal AS retreat_total,
    v.name AS venue_name,  
    v.city AS venue_city,  
    v.state AS venue_state,  
    p.description
FROM 
    pravachans p
JOIN 
    retreats r ON p.retreatid = r.id
JOIN 
    venues v ON p.venueID = v.id  
ORDER BY 
    p.date;

    """
    
    cursor.execute(query)
    pravachans = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return render_template('retreats.html', pravachans=pravachans)

from datetime import datetime

@app.route('/pravachan/<pravachan_id>', methods=['GET', 'POST'])
def pravachan_page(pravachan_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        # Get the form data
        index = request.form['index']
        indexNm = request.form['indexNm']
        title = request.form['title']
        featured = request.form['featured']
        webCtgry = request.form['webCtgry']
        webSeq = request.form['webSeq']
        description = request.form['description']
        date = request.form['date']
        hour = request.form['hour']
        venue = request.form['venue']
        holyDay = request.form['holyDay']
        splOccasion = request.form['splOccasion']
        retreat = request.form['retreat']
        retreatTitl = request.form['retreatTitl']
        k_of_n = request.form['k_of_n']
        overView = request.form['overview']
        totalTime = request.form['totalTime']
        onWebForSale = request.form['onWebForSale']
        coverImg = request.form['coverImg']
        audio_A = request.form['audio_A']
        audio_B = request.form['audio_B']
        mp3Link = request.form['mp3Link']
        audioQlty = request.form['audioQlty']
        audioComments = request.form['audioComments']
        digitalData = request.form['digitalData']

        # Set the last_updated_by to the current username from the session
        last_updated_by = session['username']

        # Set the last_update_date to the current date and time
        last_update_date = datetime.now()

        # Update the database
        query = """
        UPDATE pravachans 
        SET 
            id = %s, indexNm = %s, title = %s, featured = %s, webCtgry = %s, 
            webSeq = %s, description = %s, date = %s, hour = %s, venue = %s, 
            holyDay = %s, splOccasion = %s, retreat = %s, retreatTitl = %s, 
            k_of_n = %s, overview = %s, totalTime = %s, onWebForSale = %s, 
            coverImg = %s, audio_A = %s, audio_B = %s, mp3Link = %s, 
            audioQlty = %s, audioComments = %s, digitalData = %s, 
            last_updated_by = %s, last_update_date = %s
        WHERE id = %s
        """

        cursor.execute(query, (
            index, indexNm, title, featured, webCtgry, webSeq, description, date, hour, 
            venue, holyDay, splOccasion, retreat, retreatTitl, k_of_n, overView, totalTime, 
            onWebForSale, coverImg, audio_A, audio_B, mp3Link, audioQlty, audioComments, 
            digitalData, last_updated_by, last_update_date, pravachan_id
        ))

        connection.commit()
        flash('Pravachan details updated successfully!', 'success')

    # Fetch the pravachan details for the page
    query = """
        SELECT * FROM pravachans WHERE id = %s
    """
    cursor.execute(query, (pravachan_id,))
    pravachan = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template('pravachan_details.html', pravachan=pravachan)

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
 
# @app.route('/pravachan/<pravachan_id>')
# def pravachan_page(pravachan_id):
#     connection = get_db_connection()
#     cursor = connection.cursor(dictionary=True)

#     query = """
#         SELECT * FROM Pravachans WHERE id = %s
#     """
#     cursor.execute(query, (pravachan_id,))
#     pravachan = cursor.fetchone()

#     cursor.close()
#     connection.close()

#     return render_template('pravachan_details.html', pravachan=pravachan)

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
