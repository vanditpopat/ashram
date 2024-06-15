from flask import Flask, flash, redirect, render_template, url_for
from forms.login import LoginForm
from forms.signup import SignupForm
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # In a real app, here you'd validate the user credentials
        flash('Login Requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('home'))
    return render_template('login.html', title='Sign In', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        # Here, you'd typically save the user to your database
        flash('Thanks for registering, {}!'.format(form.username.data))
        return redirect(url_for('home'))
    return render_template('signup.html', title='Sign Up', form=form)

@app.route('/webview')
def webview():
    data = [
        {'sr_no': 1, 'category': 'Books', 'link': 'https://example.com/books'},
        {'sr_no': 2, 'category': 'Articles', 'link': 'https://example.com/articles'},
        {'sr_no': 3, 'category': 'Videos', 'link': 'https://example.com/videos'}
    ]
    return render_template('web_view.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)