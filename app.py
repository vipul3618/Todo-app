import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from dotenv import load_dotenv
import os
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'sunbeam')

@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}

# Database configuration
def get_db():
    if not hasattr(g, 'db'):
        g.db = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'todo_user'),
            password=os.getenv('DB_PASSWORD', 'password'),
            database=os.getenv('DB_NAME', 'mytododb')
        )
    return g.db

def get_cursor():
    return get_db().cursor(dictionary=True)

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

# Helper functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def is_password_complex(password):
    return (len(password) >= 8 and 
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password))

# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not is_password_complex(password):
            flash("Password must be at least 8 characters with at least one uppercase letter and one number")
            return render_template('register.html')
        
        hashed_pw = generate_password_hash(password)
        cursor = get_cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)", 
                (username, hashed_pw)
            )
            get_db().commit()
            flash("Registration successful! Please log in.")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            get_db().rollback()
            if err.errno == 1062:  # Duplicate entry error
                flash("Username already exists.")
            else:
                flash("Registration failed. Please try again.")
                app.logger.error(f"Registration error: {err}")
        finally:
            cursor.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = get_cursor()
        
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('index'))
            flash("Invalid credentials.")
        except mysql.connector.Error as err:
            flash("Login failed. Please try again.")
            app.logger.error(f"Login error: {err}")
        finally:
            cursor.close()
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
@login_required
def index():
    status_filter = request.args.get('status')
    query = "SELECT * FROM tasks WHERE user_id = %s"
    params = [session['user_id']]

    if status_filter in ['Pending', 'Completed']:
        query += " AND status = %s"
        params.append(status_filter)

    cursor = get_cursor()
    try:
        cursor.execute(query, tuple(params))
        tasks = cursor.fetchall()
        return render_template('index.html', 
                             tasks=tasks, 
                             username=session.get('username'), 
                             filter=status_filter or '')
    except mysql.connector.Error as err:
        flash("Error loading tasks.")
        app.logger.error(f"Task loading error: {err}")
        return render_template('index.html', tasks=[], username=session.get('username'))
    finally:
        cursor.close()

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    name = request.form['task_name']
    status = request.form['status']
    priority = request.form.get('priority', 'Medium')  # Default to Medium if not provided
    cursor = get_cursor()
    
    try:
        cursor.execute(
            "INSERT INTO tasks (name, status, priority, user_id) VALUES (%s, %s, %s, %s)", 
            (name, status, priority, session['user_id'])
        )
        get_db().commit()
    except mysql.connector.Error as err:
        get_db().rollback()
        flash("Failed to add task.")
        app.logger.error(f"Add task error: {err}")
    finally:
        cursor.close()
    
    return redirect(url_for('index'))


@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    cursor = get_cursor()
    try:
        cursor.execute(
            "DELETE FROM tasks WHERE id = %s AND user_id = %s", 
            (task_id, session['user_id'])
        )
        get_db().commit()
    except mysql.connector.Error as err:
        get_db().rollback()
        flash("Failed to delete task.")
        app.logger.error(f"Delete task error: {err}")
    finally:
        cursor.close()
    
    return redirect(url_for('index'))

@app.route('/complete_task/<int:task_id>')
@login_required
def complete_task(task_id):
    cursor = get_cursor()
    try:
        cursor.execute(
            """UPDATE tasks 
               SET status = 'Completed', completed_at = NOW() 
               WHERE id = %s AND user_id = %s""",
            (task_id, session['user_id'])
        )
        get_db().commit()
    except mysql.connector.Error as err:
        get_db().rollback()
        flash("Failed to complete task.")
        app.logger.error(f"Complete task error: {err}")
    finally:
        cursor.close()
    
    return redirect(url_for('index'))

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    cursor = get_cursor()
    try:
        if request.method == 'POST':
            new_name = request.form['task_name']
            cursor.execute(
                """UPDATE tasks 
                   SET name = %s 
                   WHERE id = %s AND user_id = %s""",
                (new_name, task_id, session['user_id'])
            )
            get_db().commit()
            return redirect(url_for('index'))
        
        cursor.execute(
            "SELECT * FROM tasks WHERE id = %s AND user_id = %s", 
            (task_id, session['user_id'])
        )
        task = cursor.fetchone()
        return render_template('edit_task.html', task=task)
    except mysql.connector.Error as err:
        get_db().rollback()
        flash("Error editing task.")
        app.logger.error(f"Edit task error: {err}")
        return redirect(url_for('index'))
    finally:
        cursor.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
