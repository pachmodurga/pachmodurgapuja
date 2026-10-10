from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, g, session, send_from_directory
import os
import psycopg2
import psycopg2.extras
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# सेशन को परमानेंट मार्क करें और 10 मिनट का टाइमआउट सेट करें
app.permanent_session_lifetime = timedelta(minutes=10)

DATABASE_URL = os.environ.get('DATABASE_URL')
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.before_request
def make_session_permanent():
    session.permanent = True

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        if DATABASE_URL:
            db = g._database = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            raise RuntimeError("DATABASE_URL environment variable is not set!")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collections (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                vendor TEXT,
                amount REAL NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

# ऐप शुरू होते ही टेबल बनाने के लिए इनिशियलाइज़ेशन कॉल
init_db()

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'pachmo' and password == 'Pachmo#102':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('landing'))

@app.route('/dashboard')
def dashboard():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM collections")
    total_collection = cursor.fetchone()['coalesce']

    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM expenses")
    total_expenses = cursor.fetchone()['coalesce']

    available_balance = total_collection - total_expenses
    utilization_ratio = round((total_expenses / total_collection) * 100, 1) if total_collection > 0 else 0.0

    category_filter = request.args.get('category', 'All Categories')
    search_query = request.args.get('search', '').strip()
    
    per_page = 10
    
    # अलग-अलग पेज नंबर ट्रैकिंग
    contrib_page = int(request.args.get('contrib_page', 1))
    contrib_offset = (contrib_page - 1) * per_page

    expense_page = int(request.args.get('expense_page', 1))
    expense_offset = (expense_page - 1) * per_page

    # खर्चों के लिए क्वेरी और पैजिनेशन
    query_exp = "SELECT * FROM expenses WHERE 1=1"
    params_exp = []
    if category_filter and category_filter != 'All Categories':
        query_exp += " AND category = %s"
        params_exp.append(category_filter)
    if search_query:
        query_exp += " AND (title ILIKE %s OR vendor ILIKE %s)"
        params_exp.extend([f"%{search_query}%", f"%{search_query}%"])
    
    # कुल खर्चों की संख्या (फिल्टर के साथ या बिना)
    count_query_exp = f"SELECT COUNT(*) AS count FROM ({query_exp}) AS sub"
    cursor.execute(count_query_exp, params_exp)
    total_expenses_filtered_count = cursor.fetchone()['count']
    total_expense_pages = (total_expenses_filtered_count + per_page - 1) // per_page if total_expenses_filtered_count > 0 else 1

    query_exp += " ORDER BY id DESC LIMIT %s OFFSET %s"
    params_exp.extend([per_page, expense_offset])
    
    cursor.execute(query_exp, params_exp)
    expenses = cursor.fetchall()

    # कुल दाताओं और कुल खर्चों की समग्र संख्या (डैशबोर्ड कार्ड्स के लिए)
    cursor.execute("SELECT COUNT(*) AS count FROM collections")
    total_collections_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) AS count FROM expenses")
    total_expenses_count = cursor.fetchone()['count']

    total_contrib_pages = (total_collections_count + per_page - 1) // per_page if total_collections_count > 0 else 1

    cursor.execute("SELECT * FROM collections ORDER BY id DESC LIMIT %s OFFSET %s", (per_page, contrib_offset))
    contributions = cursor.fetchall()

    cursor.execute("SELECT * FROM uploads ORDER BY id DESC")
    uploads = cursor.fetchall()

    return render_template(
        'index.html',
        total_collection=total_collection,
        total_expenses=total_expenses,
        available_balance=available_balance,
        utilization_ratio=utilization_ratio,
        expenses=expenses,
        contributions=contributions,
        uploads=uploads,
        selected_category=category_filter,
        search_query=search_query,
        contrib_page=contrib_page,
        total_contrib_pages=total_contrib_pages,
        expense_page=expense_page,
        total_expense_pages=total_expense_pages,
        total_collections_count=total_collections_count,
        total_expenses_count=total_expenses_count
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO uploads (filename) VALUES (%s)", (filename,))
        db.commit()
    return redirect(url_for('dashboard'))

@app.route('/uploads/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete_upload/<int:id>', methods=['POST'])
def delete_upload(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT filename FROM uploads WHERE id = %s", (id,))
    upload = cursor.fetchone()
    if upload:
        filename = upload['filename']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        cursor.execute("DELETE FROM uploads WHERE id = %s", (id,))
        db.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_contribution', methods=['POST'])
def add_contribution():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    if name and amount > 0:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO collections (name, amount) VALUES (%s, %s)", (name, amount))
        db.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    title = request.form.get('title')
    category = request.form.get('category')
    vendor = request.form.get('vendor')
    amount = float(request.form.get('amount', 0))
    if title and category and amount > 0:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO expenses (title, category, vendor, amount) VALUES (%s, %s, %s, %s)",
                   (title, category, vendor, amount))
        db.commit()
    return redirect(url_for('dashboard'))

@app.route('/edit_contribution/<int:id>', methods=['POST'])
def edit_contribution(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE collections SET name = %s, amount = %s WHERE id = %s", (name, amount, id))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/edit_expense/<int:id>', methods=['POST'])
def edit_expense(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    title = request.form.get('title')
    category = request.form.get('category')
    vendor = request.form.get('vendor')
    amount = float(request.form.get('amount', 0))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE expenses SET title = %s, category = %s, vendor = %s, amount = %s WHERE id = %s", 
               (title, category, vendor, amount, id))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_expense/<int:id>', methods=['POST'])
def delete_expense(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_contribution/<int:id>', methods=['POST'])
def delete_contribution(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM collections WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route('/download_contribution_report')
def download_contribution_report():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM collections ORDER BY id DESC")
    contributions = cursor.fetchall()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM collections")
    total = cursor.fetchone()['coalesce']
    return render_template('report_print.html', title="चंदा रिपोर्ट", data=contributions, total=total, type="contrib")

@app.route('/download_expense_report')
def download_expense_report():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY id DESC")
    expenses = cursor.fetchall()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM expenses")
    total = cursor.fetchone()['coalesce']
    return render_template('report_print.html', title="खर्च रिपोर्ट", data=expenses, total=total, type="expense")

@app.route('/download_full_report')
def download_full_report():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM collections ORDER BY id DESC")
    contributions = cursor.fetchall()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM collections")
    total_collection = cursor.fetchone()['coalesce']
    cursor.execute("SELECT * FROM expenses ORDER BY id DESC")
    expenses = cursor.fetchall()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM expenses")
    total_expenses = cursor.fetchone()['coalesce']
    available_balance = total_collection - total_expenses
    utilization_ratio = round((total_expenses / total_collection) * 100, 1) if total_collection > 0 else 0.0
    return render_template('full_report_print.html', 
                           contributions=contributions, 
                           expenses=expenses, 
                           total_collection=total_collection, 
                           total_expenses=total_expenses, 
                           available_balance=available_balance,
                           utilization_ratio=utilization_ratio)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
