from flask import Flask, flash, json, redirect, render_template, session, url_for, request, jsonify
from forms.login import LoginForm
from forms.signup import SignupForm
import mysql.connector
from mysql.connector import Error
import re
from flask_bcrypt import Bcrypt
from functools import wraps
from datetime import datetime

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

from functools import wraps
from flask import abort, session

def roles_exclude(excluded_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if roles exist in the session and the user is NOT the excluded role
            if 'roles' not in session or excluded_role in session['roles']:
                abort(403)  # Forbidden access
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(role_name):
    """
    Decorator to restrict access based on the user role.
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'loggedin' not in session:
                return redirect(url_for('login'))
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # Get user's roles
            query = """
            SELECT r.name
            FROM is601_userroles ur
            JOIN is601_roles r ON ur.role_id = r.id
            WHERE ur.user_id = %s AND ur.is_active = 1
            """
            cursor.execute(query, (session['id'],))
            roles = cursor.fetchall()

            cursor.close()
            connection.close()

            # Check if user has the required role
            if role_name not in [role['name'] for role in roles]:
                flash(f'You do not have access to this page. Required role: {role_name}', 'danger')
                return redirect(url_for('home'))

            return f(*args, **kwargs)
        return decorated_function
    return wrapper

@app.route('/')
def home():
    if 'loggedin' in session:
        return render_template('home_loggedin.html', username=session['username'])
    else:
        return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error_message = None
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account and bcrypt.check_password_hash(account['password'], password):
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']

            # Fetch roles and store in session
            cursor.execute("""
                SELECT r.name 
                FROM is601_userroles ur
                JOIN is601_roles r ON ur.role_id = r.id
                WHERE ur.user_id = %s AND ur.is_active = 1
            """, (account['id'],))
            roles = cursor.fetchall()
            session['roles'] = [role['name'] for role in roles]
            flash('You have viewers privileges. For more privileges, contact the ashram.', 'info')
            print(session['roles'])  # Debugging to ensure roles are set correctly
            return redirect(url_for('home'))
        else:
            error_message = 'Incorrect username or password!'

        cursor.close()
        connection.close()

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

                    # Fetch the newly created user id
                    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                    user = cursor.fetchone()

                    # Assign 'viewer' role to the newly created user
                    cursor.execute("SELECT id FROM is601_roles WHERE name = 'viewer'")
                    viewer_role = cursor.fetchone()

                    if viewer_role:
                        cursor.execute("INSERT INTO is601_userroles (role_id, user_id, is_active) VALUES (%s, %s, %s)", 
                                       (viewer_role['id'], user['id'], 1))
                        connection.commit()

                    # Automatically log the user in after signup
                    session['loggedin'] = True
                    session['id'] = user['id']
                    session['username'] = username

                    # Assign the roles to session
                    cursor.execute("""
                        SELECT r.name 
                        FROM is601_userroles ur
                        JOIN is601_roles r ON ur.role_id = r.id
                        WHERE ur.user_id = %s AND ur.is_active = 1
                    """, (user['id'],))
                    roles = cursor.fetchall()
                    session['roles'] = [role['name'] for role in roles]

                    flash('You have successfully signed up and are logged in!', 'success')
                    flash('You have viewers privileges. For more privileges, contact the ashram.', 'info')

                    return redirect(url_for('home'))
            
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
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
@role_required('viewer')  # Allow all roles except anonymous
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute('SELECT email, username FROM users WHERE id = %s', (session['id'],))
    user_info = cursor.fetchone()

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

@app.route('/manageprofiles')
@roles_exclude('viewer')  # Only accessible to non-viewer roles
def manage_profiles():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch users and their roles
    query = """
    SELECT u.id, u.username, r.name AS role
    FROM users u
    JOIN is601_userroles ur ON u.id = ur.user_id
    JOIN is601_roles r ON ur.role_id = r.id
    WHERE ur.is_active = 1
    """
    cursor.execute(query)
    users = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('manage_profiles.html', users=users)

@app.route('/retreat')
@role_required('viewer')
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
    FROM pravachans p
    JOIN retreats r ON p.retreatid = r.id
    JOIN venues v ON p.venueID = v.id
    ORDER BY p.date;
    """
    
    cursor.execute(query)
    pravachans = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return render_template('retreats.html', pravachans=pravachans)

@app.route('/pravachan/<pravachan_id>', methods=['GET', 'POST'])
@role_required('author')  # Only authors and higher roles can access pravachan details
def pravachan_page(pravachan_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        # Get the form data from the request
        title = request.form['title']
        IndexNM = request.form['IndexNM']
        date = request.form['date']
        hour = request.form['hour']
        description = request.form['description']
        totalTime = request.form['totalTime']
        onWebForSale = request.form['onWebForSale']
        featured = request.form['featured']
        comments = request.form['comments']
        webseq = request.form['webSeq']
        retreatNumber = request.form['retreatNumber']
        retreatid = request.form['retreat']
        venueid = request.form['venue']
        holyday = request.form['holyDay']
        splOccasion = request.form['splOccasion']
        audioLinkA = request.form['audio_A']
        audioLinkB = request.form['audio_B']
        mp3Link = request.form['mp3Link']
        column_8 = request.form['column_8']
        docRef = request.form['docRef']
        coverImg = request.form['coverImg']
        digitalData = request.form['digitalData']
        audioQualitycode = request.form['audioQlty']
        webcatid = request.form['webCtgry']

        # Set the last_updated_by to the current username from the session
        last_updated_by = session['username']
        last_update_date = datetime.now()

        # Update the database for pravachans table and related tables
        update_pravachan_query = """
        UPDATE pravachans 
        SET title = %s, IndexNM= %s, date = %s, hour = %s, description = %s, 
            TotalTime = %s, OnWebForSale = %s, featured = %s, comments = %s, 
            webseq = %s, retreatNumber = %s, retreatid = %s, venueID = %s, 
            Holydayref = %s, splocassionid = %s, webcatid = %s, 
            last_updated_by = %s, last_update_date = %s
        WHERE id = %s
        """
        cursor.execute(update_pravachan_query, (
            title, IndexNM, date, hour, description, totalTime, onWebForSale, featured, 
            comments, webseq, retreatNumber, retreatid, venueid, 
            holyday, splOccasion, webcatid, last_updated_by, last_update_date, pravachan_id
        ))

        # Update the audios table
        update_audio_query = """
        UPDATE audios 
        SET AudioLinkA = %s, AudioLinkB = %s, mp3Link = %s, column_8 = %s
        WHERE pravachanid = %s
        """
        cursor.execute(update_audio_query, (
            audioLinkA, audioLinkB, mp3Link, column_8, pravachan_id
        ))

        # Update the docs table
        update_docs_query = """
        UPDATE docs 
        SET DocRef = %s, CoverImg = %s, DigitalData = %s
        WHERE pravachanid = %s
        """
        cursor.execute(update_docs_query, (
            docRef, coverImg, digitalData, pravachan_id
        ))

        connection.commit()
        flash('Pravachan details updated successfully!', 'success')

    # Fetch the pravachan details for the page using your complex query
    query = """
    SELECT 
        p.title AS pravachan_title,
        p.id AS pravachan_id,
        p.IndexNM,
        p.date,
        p.hour,
        p.description,
        p.TotalTime,
        p.OnWebForSale,
        p.featured,
        p.comments,
        p.webseq,
        p.retreatNumber,
        r.retreatTitle AS retreat_title,
        r.retreatTotal AS retreattotal,
        v.name AS venue_name,  
        v.city AS venue_city,  
        v.state AS venue_state, 
        h.holyday AS holy_day,
        s.sploccasion AS special_occassion,
        a.AudioLinkA,
        a.AudioLinkB,
        a.mp3Link,
        a.column_8,
        d.DocRef,
        d.CoverImg,
        d.DigitalData,
        aq.AudioQualCode,
        aq.AudioQualCodeDesp,
        w.categoryname 
    FROM 
        pravachans p
    LEFT JOIN 
        retreats r ON p.retreatid = r.id
    LEFT JOIN 
        venues v ON p.venueID = v.id  
    LEFT JOIN 
        holydays h ON p.Holydayref = h.holydayid 
    LEFT JOIN 
        audios a ON p.id = a.pravachanid  
    LEFT JOIN 
        docs d ON p.id = d.pravachanid
    LEFT JOIN 
        specialoccasions s ON p.splocassionid = s.sqloccid 
    LEFT JOIN 
        audioqualities aq ON aq.id = a.AudioQualid
    LEFT JOIN 
        webcategories w ON p.webcatid = w.id 
    WHERE p.id = %s
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
@role_required('viewer')  # Allow viewers or higher roles
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

@app.route('/satsangs')
@role_required('viewer')  # Allow viewers or higher roles
def index_counts():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

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

    half = len(index_counts) // 2
    first_column_data = index_counts[:half]
    second_column_data = index_counts[half:]

    return render_template('satsang.html', first_column_data=first_column_data, second_column_data=second_column_data)

@app.route('/email')
@role_required('viewer')  # Allow viewers or higher roles
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
