from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, g, session, jsonify
import os
import sqlite3
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

app.permanent_session_lifetime = timedelta(minutes=10)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'puja_portal.db')

cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

@app.before_request
def make_session_permanent():
    session.permanent = True

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                puja_name TEXT DEFAULT 'दुर्गा पूजा',
                year INTEGER DEFAULT 2026,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS non_donors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                puja_name TEXT DEFAULT 'दुर्गा पूजा',
                year INTEGER DEFAULT 2026,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                vendor TEXT,
                amount REAL NOT NULL,
                puja_name TEXT DEFAULT 'दुर्गा पूजा',
                year INTEGER DEFAULT 2026,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_url TEXT,
                puja_name TEXT DEFAULT 'दुर्गा पूजा',
                year INTEGER DEFAULT 2026,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # पोर्टल लॉक और 6-अंकों के पिन मैनेजमेंट के लिए (डिफ़ॉल्ट पिन '822116')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portal_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                puja_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                is_locked INTEGER DEFAULT 0,
                pin TEXT DEFAULT '822116',
                UNIQUE(puja_name, year)
            )
        ''')
        db.commit()

        # डिफ़ॉल्ट डेटा पापुलेशन
        cursor.execute("SELECT COUNT(*) AS cnt FROM collections WHERE puja_name = 'दुर्गा पूजा' AND year = 2026")
        if cursor.fetchone()['cnt'] == 0:
            pdf_contributions = [
                ('गोपाल मेहता', 500.0, '2026-10-20 05:12:16'),
                ('अजय राजवंशी (वर्तमान मुखिया)', 2000.0, '2026-10-20 04:52:26'),
                ('Ranjeet paswan (jila parishad pratyashi)', 500.0, '2026-10-20 04:45:09'),
                ('Ganeshi ram', 101.0, '2026-10-19 07:38:13'),
                ('कृष्णा बैठा जिला परिषद प्रत्याशी', 500.0, '2026-10-19 07:08:57'),
                ('मदन पासवान जिला परिषद', 500.0, '2026-10-19 01:40:12'),
                ('सुरेंद्र मेहता', 501.0, '2026-10-19 01:38:58'),
                ('Shambhu Mehta', 501.0, '2026-10-18 04:54:02'),
                ('Suresh rajwar पूर्व पंचायत समिति', 200.0, '2026-10-18 02:56:33'),
                ('शिवशंकर मेहता', 5100.0, '2026-10-18 01:59:45'),
                ('Amit Kumar (Gandhi) मुखिया उम्मीदवार', 500.0, '2026-10-18 00:56:03'),
                ('Suresh mehta', 500.0, '2026-10-17 04:34:01'),
                ('Rajendra Mehta', 551.0, '2026-10-17 03:50:49'),
                ('Jagdish yadav', 501.0, '2026-10-17 03:50:34'),
                ('Haricharan mehta', 551.0, '2026-10-16 10:05:43'),
                ('Devendra mehta', 501.0, '2026-10-16 08:52:12'),
                ('Arun mehta', 551.0, '2026-10-16 08:51:48'),
                ('Vinod mehta', 500.0, '2026-10-16 08:51:33'),
                ('Upendra mehta', 500.0, '2026-10-16 08:51:17'),
                ('Kamendra mehta', 502.0, '2026-10-16 08:51:00'),
                ('Arvind mehta', 500.0, '2026-10-16 08:50:11'),
                ('Sarayu mehta', 501.0, '2026-10-16 00:01:16'),
                ('Namneshwar mehta', 500.0, '2026-10-15 06:52:14'),
                ('Birendra mehta', 500.0, '2026-10-15 06:51:49'),
                ('Shree mehta', 501.0, '2026-10-15 04:51:30'),
                ('Anil mehta', 500.0, '2026-10-15 04:51:01'),
                ('Ajay mehta', 500.0, '2026-10-15 04:50:43'),
                ('Sumit prasad mehta', 501.0, '2026-10-15 04:50:24'),
                ('Birendra mehta', 500.0, '2026-10-15 04:48:55'),
                ('Pramod thakur', 500.0, '2026-10-15 04:48:24'),
                ('Dharmendra mehta', 500.0, '2026-10-15 04:48:05'),
                ('Deelip mehta (lakhan mehta)', 501.0, '2026-10-15 04:47:06'),
                ('SANJAY MEHTA', 500.0, '2026-10-14 13:09:16'),
                ('Rampravesh yadav', 500.0, '2026-10-14 13:08:45'),
                ('Arjun mehta', 521.0, '2026-10-14 12:18:32'),
                ('Sanjeev kumar', 501.0, '2026-10-14 09:28:15'),
                ('शिवकुमार mehta', 501.0, '2026-10-13 12:07:14'),
                ('Vivek (jitendra mehta)', 501.0, '2026-10-13 04:55:12'),
                ('Ravindra mehta', 501.0, '2026-10-13 02:58:04'),
                ('Rameshwar mehta', 511.0, '2026-10-13 02:57:43'),
                ('Bimlesh mehta', 501.0, '2026-10-13 02:57:00'),
                ('Banarasi mehta', 500.0, '2026-10-13 01:37:03'),
                ('Pankaj mehta', 500.0, '2026-10-12 12:55:41'),
                ('Vijay mehta', 501.0, '2026-10-12 12:48:54'),
                ('Ramchandra mehta', 501.0, '2026-10-12 09:58:43'),
                ('Nandu mehta', 501.0, '2026-10-12 06:01:37'),
                ('MAHENDRA YADAV', 501.0, '2026-10-12 05:58:15'),
                ('Umesh mehta', 501.0, '2026-10-12 05:54:21'),
                ('Santosh yadav', 500.0, '2026-10-12 02:02:32'),
                ('Satyendra yadav', 500.0, '2026-10-12 02:02:16'),
                ('Harendra yadav', 500.0, '2026-10-12 02:01:59'),
                ('Govind mehta', 501.0, '2026-10-12 02:01:43'),
                ('Keshwar mehta (Satyendra mehta)', 501.0, '2026-10-12 02:01:23'),
                ('Dhramendra mehta (मिस्त्री)', 502.0, '2026-10-12 02:00:52'),
                ('Bijendra Mehta', 500.0, '2026-10-12 02:00:09'),
                ('Niranjan mehta', 500.0, '2026-10-12 00:59:42'),
                ('Ramvinay मेहता (सुदामा मेहता उपेंद्र मेहता)', 1001.0, '2026-10-11 12:44:42'),
                ('Dhananjay mehta (Radhe)', 500.0, '2026-10-11 09:20:08'),
                ('Bachan mehta', 510.0, '2026-10-11 06:19:40'),
                ('Kameshwar mehta', 501.0, '2026-10-11 04:13:37'),
                ('Vinod thakur', 500.0, '2026-10-11 03:15:23'),
                ('Shyamsundar mehta', 500.0, '2026-10-11 01:49:47'),
                ('Chandan vishwakarma', 251.0, '2026-10-11 01:49:27'),
                ('Sumer mehta', 501.0, '2026-10-11 01:49:11'),
                ('Arun mehta', 500.0, '2026-10-11 01:49:00'),
                ('Mithlesh mehta', 500.0, '2026-10-11 01:48:49'),
                ('Pramod mehta (guddu)', 500.0, '2026-10-11 01:48:28'),
                ('Mahendra mehta', 500.0, '2026-10-11 01:48:08'),
                ('Uday mehta', 500.0, '2026-10-11 01:47:48'),
                ('Naresh mehta', 500.0, '2026-10-11 01:47:32'),
                ('Ramjanm mehta', 500.0, '2026-10-11 01:47:19'),
                ('Krishna Mehta', 501.0, '2026-10-10 12:41:23'),
                ('Ramesh Mehta', 501.0, '2026-10-10 07:59:48'),
                ('Satnarayan Mehta', 500.0, '2026-10-10 07:59:37'),
                ('Ganesh Mehta contactor', 501.0, '2026-10-10 07:58:51'),
                ('Ganesh Mehta', 501.0, '2026-10-10 07:58:08'),
                ('Ajay Yadav', 500.0, '2026-10-10 07:57:58'),
                ('Brajendra Yadav', 500.0, '2026-10-10 07:57:50'),
                ('Ramjeet Mehta', 500.0, '2026-10-10 07:57:39'),
                ('Satyendra Mehta', 500.0, '2026-10-10 07:57:30'),
                ('Parbal Mehta', 500.0, '2026-10-10 07:57:20'),
                ('Jitendra Yadav', 500.0, '2026-10-10 07:57:07'),
                ('Nagesh Mehta', 500.0, '2026-10-10 07:56:57'),
                ('Awdhesh Mehta (Rambilash Mehta)', 500.0, '2026-10-10 07:56:45'),
                ('Janeshwar Mehta', 501.0, '2026-10-10 07:56:00'),
                ('Birendra Mehta', 500.0, '2026-10-10 07:55:46'),
                ('Awdhesh Mehta', 502.0, '2026-10-10 07:55:33'),
                ('Ritesh Mehta', 500.0, '2026-10-10 07:55:17'),
                ('Manoj Mehta', 500.0, '2026-10-10 07:54:58'),
                ('Basudev Mehta', 500.0, '2026-10-10 07:54:45'),
                ('Dr Satyendra Mehta', 500.0, '2026-10-10 07:54:28'),
                ('RamPravesh Mehta contractor', 501.0, '2026-10-10 07:54:09'),
                ('Nilesh Mehta', 500.0, '2026-10-10 07:53:43'),
                ('Ranjendra Mehta', 500.0, '2026-10-10 07:53:29')
            ]
            for c in pdf_contributions:
                cursor.execute("INSERT INTO collections (name, amount, puja_name, year, date) VALUES (?, ?, 'दुर्गा पूजा', 2026, ?)", c)

        cursor.execute("SELECT COUNT(*) AS cnt FROM non_donors WHERE puja_name = 'दुर्गा पूजा' AND year = 2026")
        if cursor.fetchone()['cnt'] == 0:
            pdf_non_donors = [
                ('Rukesh Mehta (Dhaneshwar Mehta)', '2026-10-21 04:08:05'),
                ('Sunil Mehta', '2026-10-21 04:07:18'),
                ('Shyam Sunder Mehta', '2026-10-21 04:07:05'),
                ('Harendra Mehta (Lakhan Mehta )', '2026-10-21 04:06:46'),
                ('Lalu Mehta (Lakhan Mehta )', '2026-10-21 04:06:12'),
                ('Mithilesh Mehta (Lakhan Mehta )', '2026-10-21 04:05:23'),
                ('Vishwanath Mehta', '2026-10-21 04:04:14'),
                ('Anand Mehta', '2026-10-21 04:03:39'),
                ('Virenda Mehta', '2026-10-21 04:03:23'),
                ('Dinesh Mehta', '2026-10-21 04:03:08'),
                ('Aklesh Mehta', '2026-10-21 04:02:10')
            ]
            for nd in pdf_non_donors:
                cursor.execute("INSERT INTO non_donors (name, puja_name, year, date) VALUES (?, 'दुर्गा पूजा', 2026, ?)", nd)

        cursor.execute("SELECT COUNT(*) AS cnt FROM expenses WHERE puja_name = 'दुर्गा पूजा' AND year = 2026")
        if cursor.fetchone()['cnt'] == 0:
            pdf_expenses = [
                ('Mali ka paisa', 'Logistics & Misc', '', 600.0, '2026-10-21 03:19:01'),
                ('Sonu ke dukan se laya gya saman', 'Artists & Dhaki', '', 365.0, '2026-10-21 02:55:09'),
                ('Phul sajawat k', 'Pandal & Decor', '', 400.0, '2026-10-21 02:41:44'),
                ('Thakur ji ke', 'Artists & Dhaki', '', 600.0, '2026-10-21 02:15:06'),
                ('Tractor bhara', 'Other', '', 800.0, '2026-10-21 02:13:56'),
                ('Kalash Yatra me pickup ka bhara and diseal', 'Lighting & Sound', '', 1250.0, '2026-10-21 02:12:45'),
                ('Julush me dj', 'Lighting & Sound', '', 3000.0, '2026-10-21 02:09:07'),
                ('Booking amount me jama', 'Lighting & Sound', '', 1750.0, '2026-10-21 02:08:18'),
                ('Pandiji ka paisa', 'Other', '', 5401.0, '2026-10-20 12:17:19'),
                ('Pandiji ko pahuchane me', 'Other', '', 60.0, '2026-10-20 09:45:36'),
                ('मुरही', 'Bhog & Prasad', '', 160.0, '2026-10-20 08:01:09'),
                ('डीजल जरनेटर और पिकअप में', 'Lighting & Sound', '', 1000.0, '2026-10-20 06:33:36'),
                ('Pandiji ko lane and pahuchane me', 'Other', '', 100.0, '2026-10-19 07:09:32'),
                ('Booking amount me jama', 'Lighting & Sound', '', 700.0, '2026-10-19 01:43:08'),
                ('बूंदिया बनाई यमुना मेहता', 'Bhog & Prasad', '', 500.0, '2026-10-19 01:40:55'),
                ('Pandiji ko lane and pahuchane me', 'Other', '', 100.0, '2026-10-18 07:23:50'),
                ('रोड़ी गुलाल सिंदूर और चंदन', 'Logistics & Misc', '', 30.0, '2026-10-18 04:53:36'),
                ('झोला प्रसाद वितरण करने के लिए 4 pcs', 'Bhog & Prasad', '', 80.0, '2026-10-18 00:58:23'),
                ('Diseal', 'Lighting & Sound', '', 500.0, '2026-10-18 00:55:06'),
                ('Pandiji ko lane and pahuchane me', 'Other', '', 120.0, '2026-10-18 00:54:09'),
                ('Raju k booking me jama', 'Lighting & Sound', '', 10000.0, '2026-10-17 07:45:57'),
                ('Ganeshi ram', 'Artists & Dhaki', '', 500.0, '2026-10-17 04:34:54'),
                ('Raju k booking me jama', 'Lighting & Sound', '', 551.0, '2026-10-16 13:32:25'),
                ('Elaichi dana', 'Bhog & Prasad', '', 50.0, '2026-10-16 13:16:08'),
                ('Besan and bhang', 'Bhog & Prasad', '', 260.0, '2026-10-16 13:03:24'),
                ('Prasad packing plastik', 'Bhog & Prasad', '', 200.0, '2026-10-16 09:47:34'),
                ('Coin mandir me diye the', 'Other', '', 10.0, '2026-10-16 09:10:49'),
                ('Pandiji ko lane and pahuchane', 'Other', '', 100.0, '2026-10-16 08:58:57'),
                ('Prasad k saman', 'Bhog & Prasad', '', 8800.0, '2026-10-16 08:43:13'),
                ('Mouli dhaga', 'Logistics & Misc', '', 100.0, '2026-10-15 08:29:33'),
                ('Pandiji ko lane and pahuchane k liye', 'Other', '', 100.0, '2026-10-15 06:53:02'),
                ('Pandiji ko lane and pahuchane me', 'Other', '', 100.0, '2026-10-14 09:04:19'),
                ('चुरा, इलायची दाना, बादाम दाना', 'Bhog & Prasad', '', 380.0, '2026-10-13 11:51:16'),
                ('Pandiji ko lane and pahuchane me', 'Other', '', 100.0, '2026-10-13 02:58:52'),
                ('Pandiji ko lane and pahuchane me', 'Other', '', 100.0, '2026-10-12 07:20:43'),
                ('Pandi jii ko lalne and pahuchane', 'Other', '', 100.0, '2026-10-11 11:43:15'),
                ('पुजारी के cloth', 'Logistics & Misc', '', 500.0, '2026-10-11 08:21:23'),
                ('Banana ,apple', 'Bhog & Prasad', '', 160.0, '2026-10-11 06:20:34'),
                ('डीज़ल', 'Other', '', 500.0, '2026-10-11 03:18:47'),
                ('घी', 'Bhog & Prasad', '', 1200.0, '2026-10-11 03:13:51'),
                ('Booking amount me se jama', 'Lighting & Sound', '', 2000.0, '2026-10-11 02:02:10'),
                ('कलश में सिक्का डालने में लगे खर्च', 'Other', '', 30.0, '2026-10-10 08:13:32'),
                ('टोटल सामान को लाने में ऑटो भाड़ा', 'Logistics & Misc', '', 150.0, '2026-10-10 08:12:29'),
                ('राजू के बाइक से गए थे जपला समान और पंडित जी को लाने में', 'Other', '', 100.0, '2026-10-10 08:11:56'),
                ('कलश यात्रा में डीजल जरनेटर me', 'Lighting & Sound', '', 900.0, '2026-10-10 08:11:22'),
                ('फल', 'Bhog & Prasad', '', 420.0, '2026-10-10 08:10:32'),
                ('चुका ढक्कन', 'Idol & Pratima', '', 900.0, '2026-10-10 08:10:05'),
                ('बैंजो बाजा', 'Lighting & Sound', '', 3000.0, '2026-10-10 08:09:34'),
                ('झंडा', 'Idol & Pratima', '', 100.0, '2026-10-10 08:09:00'),
                ('सिंगर समान', 'Other', '', 105.0, '2026-10-10 08:07:29'),
                ('कपड़ा', 'Other', '', 750.0, '2026-10-10 08:05:14'),
                ('Puja Saman (पूजा समान)', 'Bhog & Prasad', '', 2965.0, '2026-10-10 08:02:05')
            ]
            for exp in pdf_expenses:
                cursor.execute("INSERT INTO expenses (title, category, vendor, amount, puja_name, year, date) VALUES (?, ?, ?, ?, 'दुर्गा पूजा', 2026, ?)", exp)

        db.commit()

init_db()

# सुरक्षा चेकर फंक्शन
def is_portal_locked(puja_name, year):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT is_locked FROM portal_locks WHERE puja_name = ? AND year = ?", (puja_name, year))
    row = cursor.fetchone()
    return row['is_locked'] == 1 if row else False

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    current_year = datetime.now().year
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        puja = request.form.get('puja_name', 'दुर्गा पूजा')
        year = int(request.form.get('year', current_year))
        if username == 'pachmo' and password == 'Pachmo#102':
            session['logged_in'] = True
            session['selected_puja'] = puja
            session['selected_year'] = year
            return redirect(url_for('dashboard', puja=puja, year=year))
        else:
            return "Invalid username or password"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('selected_puja', None)
    session.pop('selected_year', None)
    return redirect(url_for('landing'))

# लॉक स्टेटस चेक करने के लिए
@app.route('/check_lock', methods=['GET'])
def check_lock():
    puja_name = request.args.get('puja', 'दुर्गा पूजा')
    year = int(request.args.get('year', datetime.now().year))
    locked = is_portal_locked(puja_name, year)
    return jsonify({'locked': locked})

# पिन वेरीफाई करके 6-अंकों के पिन (822116) के साथ लॉक/अनलॉक टॉगल करने के लिए
@app.route('/toggle_lock', methods=['POST'])
def toggle_lock():
    data = request.json
    puja_name = data.get('puja_name', 'दुर्गा पूजा')
    year = int(data.get('year', datetime.now().year))
    entered_pin = data.get('pin', '').strip()
    action = data.get('action') # 'lock' या 'unlock'

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT pin FROM portal_locks WHERE puja_name = ? AND year = ?", (puja_name, year))
    row = cursor.fetchone()

    # डिफ़ॉल्ट पिन 822116 यदि सेट नहीं है
    db_pin = row['pin'] if row else '822116'
    if row is None:
        cursor.execute("INSERT INTO portal_locks (puja_name, year, is_locked, pin) VALUES (?, ?, 0, '822116')", (puja_name, year))
        db.commit()

    if entered_pin != db_pin:
        return jsonify({'success': False, 'message': 'गलत सुरक्षा पिन (Incorrect PIN)! कृपया सही 6-अंकों का पिन दर्ज करें।'})

    new_lock_state = 1 if action == 'lock' else 0
    cursor.execute("UPDATE portal_locks SET is_locked = ? WHERE puja_name = ? AND year = ?", (new_lock_state, puja_name, year))
    db.commit()

    status_str = "लॉक्क (Locked)" if new_lock_state == 1 else "अन-लॉक्क (Unlocked)"
    return jsonify({'success': True, 'message': f"पोर्टल सफलतापूर्वक {status_str} कर दिया गया है।", 'locked': new_lock_state})

@app.route('/dashboard')
def dashboard():
    current_year = datetime.now().year
    puja_name = request.args.get('puja', session.get('selected_puja', 'दुर्गा पूजा'))
    year = int(request.args.get('year', session.get('selected_year', current_year)))
    
    locked_state = is_portal_locked(puja_name, year)

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM collections WHERE puja_name = ? AND year = ?", (puja_name, year))
    total_collection = cursor.fetchone()['coalesce']

    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM expenses WHERE puja_name = ? AND year = ?", (puja_name, year))
    total_expenses = cursor.fetchone()['coalesce']

    available_balance = total_collection - total_expenses
    utilization_ratio = round((total_expenses / total_collection) * 100, 1) if total_collection > 0 else 0.0

    category_filter = request.args.get('category', 'All Categories')
    search_query = request.args.get('search', '').strip()
    
    per_page = 10
    contrib_page = int(request.args.get('contrib_page', 1))
    non_donor_page = int(request.args.get('non_donor_page', 1))
    expense_page = int(request.args.get('expense_page', 1))

    contrib_offset = (contrib_page - 1) * per_page
    non_donor_offset = (non_donor_page - 1) * per_page
    expense_offset = (expense_page - 1) * per_page

    query_exp = "SELECT * FROM expenses WHERE puja_name = ? AND year = ?"
    params_exp = [puja_name, year]
    if category_filter and category_filter != 'All Categories':
        query_exp += " AND category = ?"
        params_exp.append(category_filter)
    if search_query:
        query_exp += " AND (title LIKE ? OR vendor LIKE ?)"
        params_exp.extend([f"%{search_query}%", f"%{search_query}%"])
    
    cursor.execute(f"SELECT COUNT(*) AS count FROM ({query_exp})", params_exp)
    total_expenses_filtered_count = cursor.fetchone()['count']
    total_expense_pages = (total_expenses_filtered_count + per_page - 1) // per_page if total_expenses_filtered_count > 0 else 1

    query_exp += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params_exp.extend([per_page, expense_offset])
    cursor.execute(query_exp, params_exp)
    expenses = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS count FROM collections WHERE puja_name = ? AND year = ?", (puja_name, year))
    total_collections_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) AS count FROM non_donors WHERE puja_name = ? AND year = ?", (puja_name, year))
    total_non_donors_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM expenses WHERE puja_name = ? AND year = ?", (puja_name, year))
    total_expenses_count = cursor.fetchone()['count']

    total_contrib_pages = (total_collections_count + per_page - 1) // per_page if total_collections_count > 0 else 1
    total_non_donor_pages = (total_non_donors_count + per_page - 1) // per_page if total_non_donors_count > 0 else 1

    cursor.execute("SELECT * FROM collections WHERE puja_name = ? AND year = ? ORDER BY id DESC LIMIT ? OFFSET ?", (puja_name, year, per_page, contrib_offset))
    contributions = cursor.fetchall()

    cursor.execute("SELECT * FROM non_donors WHERE puja_name = ? AND year = ? ORDER BY id DESC LIMIT ? OFFSET ?", (puja_name, year, per_page, non_donor_offset))
    non_donors = cursor.fetchall()

    cursor.execute("SELECT * FROM uploads WHERE puja_name = ? AND year = ? ORDER BY id DESC", (puja_name, year))
    uploads = cursor.fetchall()

    return render_template(
        'index.html',
        puja_name=puja_name,
        year=year,
        locked_state=locked_state,
        total_collection=total_collection,
        total_expenses=total_expenses,
        available_balance=available_balance,
        utilization_ratio=utilization_ratio,
        expenses=expenses,
        contributions=contributions,
        non_donors=non_donors,
        uploads=uploads,
        selected_category=category_filter,
        search_query=search_query,
        contrib_page=contrib_page,
        total_contrib_pages=total_contrib_pages,
        non_donor_page=non_donor_page,
        total_non_donor_pages=total_non_donor_pages,
        expense_page=expense_page,
        total_expense_pages=total_expense_pages,
        total_collections_count=total_collections_count,
        total_non_donors_count=total_non_donors_count,
        total_expenses_count=total_expenses_count
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"
    
    file = request.files.get('file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        try:
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            res_type = "raw" if ext == 'pdf' else "auto"
            upload_result = cloudinary.uploader.upload(file, resource_type=res_type)
            file_url = upload_result.get('secure_url')
        except Exception as e:
            file_url = "#"
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO uploads (filename, file_url, puja_name, year) VALUES (?, ?, ?, ?)", (filename, file_url, puja_name, year))
        db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/delete_upload/<int:id>', methods=['POST'])
def delete_upload(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    puja = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    if is_portal_locked(puja, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है।"
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM uploads WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('dashboard', puja=puja, year=year))

@app.route('/add_contribution', methods=['POST'])
def add_contribution():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    name = request.form.get('name')
    amount_str = request.form.get('amount', '').strip()
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    
    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"

    db = get_db()
    cursor = db.cursor()

    if name:
        if not amount_str or float(amount_str) == 0:
            cursor.execute("INSERT INTO non_donors (name, puja_name, year) VALUES (?, ?, ?)", (name, puja_name, year))
        else:
            amount = float(amount_str)
            cursor.execute("INSERT INTO collections (name, amount, puja_name, year) VALUES (?, ?, ?, ?)", (name, amount, puja_name, year))
        db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    title = request.form.get('title')
    category = request.form.get('category')
    vendor = request.form.get('vendor')
    amount = float(request.form.get('amount', 0))
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))

    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"

    if title and category and amount > 0:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO expenses (title, category, vendor, amount, puja_name, year) VALUES (?, ?, ?, ?, ?, ?)",
                   (title, category, vendor, amount, puja_name, year))
        db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/edit_contribution/<int:id>', methods=['POST'])
def edit_contribution(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    
    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE collections SET name = ?, amount = ? WHERE id = ?", (name, amount, id))
    db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/edit_non_donor/<int:id>', methods=['POST'])
def edit_non_donor(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    name = request.form.get('name')
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    
    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE non_donors SET name = ? WHERE id = ?", (name, id))
    db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/edit_expense/<int:id>', methods=['POST'])
def edit_expense(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    title = request.form.get('title')
    category = request.form.get('category')
    vendor = request.form.get('vendor')
    amount = float(request.form.get('amount', 0))
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    
    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE expenses SET title = ?, category = ?, vendor = ?, amount = ? WHERE id = ?", 
               (title, category, vendor, amount, id))
    db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/delete_expense/<int:id>', methods=['POST'])
def delete_expense(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    
    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/delete_contribution/<int:id>', methods=['POST'])
def delete_contribution(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    
    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM collections WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/delete_non_donor/<int:id>', methods=['POST'])
def delete_non_donor(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    puja_name = request.form.get('puja_name', 'दुर्गा पूजा')
    year = int(request.form.get('year', datetime.now().year))
    
    if is_portal_locked(puja_name, year):
        return "सुरक्षा त्रुटि: यह सत्र लॉक है। कृपया पहले अनलॉक करें।"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM non_donors WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('dashboard', puja=puja_name, year=year))

@app.route('/download_contribution_report')
def download_contribution_report():
    puja_name = request.args.get('puja', 'दुर्गा पूजा')
    year = int(request.args.get('year', datetime.now().year))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM collections WHERE puja_name = ? AND year = ? ORDER BY id DESC", (puja_name, year))
    contributions = cursor.fetchall()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM collections WHERE puja_name = ? AND year = ?", (puja_name, year))
    total = cursor.fetchone()['coalesce']
    return render_template('report_print.html', title="चंदा रिपोर्ट", data=contributions, total=total, type="contrib")

@app.route('/download_expense_report')
def download_expense_report():
    puja_name = request.args.get('puja', 'दुर्गा पूजा')
    year = int(request.args.get('year', datetime.now().year))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM expenses WHERE puja_name = ? AND year = ? ORDER BY id DESC", (puja_name, year))
    expenses = cursor.fetchall()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM expenses WHERE puja_name = ? AND year = ?", (puja_name, year))
    total = cursor.fetchone()['coalesce']
    return render_template('report_print.html', title="खर्च रिपोर्ट", data=expenses, total=total, type="expense")

@app.route('/download_full_report')
def download_full_report():
    puja_name = request.args.get('puja', 'दुर्गा पूजा')
    year = int(request.args.get('year', datetime.now().year))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM collections WHERE puja_name = ? AND year = ? ORDER BY id DESC", (puja_name, year))
    contributions = cursor.fetchall()
    cursor.execute("SELECT * FROM non_donors WHERE puja_name = ? AND year = ? ORDER BY id DESC", (puja_name, year))
    non_donors = cursor.fetchall()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM collections WHERE puja_name = ? AND year = ?", (puja_name, year))
    total_collection = cursor.fetchone()['coalesce']
    cursor.execute("SELECT * FROM expenses WHERE puja_name = ? AND year = ? ORDER BY id DESC", (puja_name, year))
    expenses = cursor.fetchall()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) AS coalesce FROM expenses WHERE puja_name = ? AND year = ?", (puja_name, year))
    total_expenses = cursor.fetchone()['coalesce']
    available_balance = total_collection - total_expenses
    utilization_ratio = round((total_expenses / total_collection) * 100, 1) if total_collection > 0 else 0.0
    return render_template('full_report_print.html', 
                           contributions=contributions, 
                           non_donors=non_donors,
                           expenses=expenses, 
                           total_collection=total_collection, 
                           total_expenses=total_expenses, 
                           available_balance=available_balance,
                           utilization_ratio=utilization_ratio)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
