from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
import json
from datetime import datetime
import uuid
from PIL import Image
import pytesseract
import io
from googletrans import Translator
import httpx

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure random key
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Initialize translator
translator = Translator()

# ================= SMS Sending Function ==================
def send_sms(phone, message):
    # api_key = "CELR3Zg21VMUIiWy4rzqnS6fYBaxNdsHlOhpJ7DQ0GFKAbTPtkNKUbiwAG0YaTfsIBxmyV4nlqJugeCR"  # Your Fast2SMS API key
    url = "https://www.fast2sms.com/dev/bulkV2"

    payload = f"sender_id=LPOINT&message={message}&language=english&route=q&numbers={phone}"
    headers = {
        # 'authorization': api_key,
        'Content-Type': "application/x-www-form-urlencoded",
        'Cache-Control': "no-cache",
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        print("SMS Response:", response.text)  # Debug output
        return response.json()  # Optional: get response as JSON
    except Exception as e:
        print("SMS Error:", str(e))
        return None

def init_db():
    # Vendors database
    conn_vendors = sqlite3.connect('vendors.db')
    c_vendors = conn_vendors.cursor()
    c_vendors.execute('''CREATE TABLE IF NOT EXISTS vendors
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 business_name TEXT NOT NULL,
                 contact_name TEXT NOT NULL,
                 email TEXT UNIQUE NOT NULL,
                 phone TEXT NOT NULL,
                 service_type TEXT NOT NULL,
                 password TEXT NOT NULL,
                 description TEXT,
                 registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 status TEXT DEFAULT 'pending')''')
    conn_vendors.commit()
    conn_vendors.close()

    # Agriculture database
    conn_agri = sqlite3.connect('agriculture.db')
    c_agri = conn_agri.cursor()
    
    c_agri.execute('''CREATE TABLE IF NOT EXISTS farmers
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             full_name TEXT NOT NULL,
             last_name TEXT NOT NULL,
             email TEXT,
             phone TEXT NOT NULL,
             farm_location TEXT NOT NULL,
             farm_size REAL,
             crop_types TEXT NOT NULL,
             password TEXT NOT NULL,
             additional_info TEXT,
             rtc_document TEXT,
             kannada_text TEXT,
             english_text TEXT,
             registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             status TEXT DEFAULT 'pending')''')
    conn_agri.commit()
    conn_agri.close()
    
    # Equipment database - CREATE ALL TABLES BEFORE CLOSING
    conn_equipment = sqlite3.connect('equipment.db')
    c_equipment = conn_equipment.cursor()
    
    c_equipment.execute('''CREATE TABLE IF NOT EXISTS equipment
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 vendor_id INTEGER NOT NULL,
                 name TEXT NOT NULL,
                 category TEXT NOT NULL,
                 description TEXT,
                 price REAL NOT NULL,
                 price_unit TEXT NOT NULL,
                 location TEXT NOT NULL,
                 status TEXT DEFAULT 'available',
                 image TEXT,
                 created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (vendor_id) REFERENCES vendors (id))''')
    
    # Bookings table
    c_equipment.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 equipment_id INTEGER NOT NULL,
                 farmer_id INTEGER NOT NULL,
                 vendor_id INTEGER NOT NULL,
                 start_date DATE NOT NULL,
                 end_date DATE NOT NULL,
                 total_amount REAL NOT NULL,
                 status TEXT DEFAULT 'pending',
                 created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (equipment_id) REFERENCES equipment (id),
                 FOREIGN KEY (farmer_id) REFERENCES farmers (id),
                 FOREIGN KEY (vendor_id) REFERENCES vendors (id))''')
    
    # Rent Requests Table - ADD THIS BEFORE CLOSING THE CONNECTION
    c_equipment.execute('''CREATE TABLE IF NOT EXISTS rent_requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 farmer_id INTEGER NOT NULL,
                 vendor_id INTEGER NOT NULL,
                 equipment_id INTEGER NOT NULL,
                 farmer_name TEXT NOT NULL,
                 farmer_phone TEXT NOT NULL,
                 equipment_name TEXT NOT NULL,
                 start_date DATE NOT NULL,
                 end_date DATE NOT NULL,
                 duration INTEGER NOT NULL,
                 purpose TEXT NOT NULL,
                 notes TEXT,
                 base_amount REAL NOT NULL,
                 service_fee REAL NOT NULL,
                 total_amount REAL NOT NULL,
                 status TEXT DEFAULT 'pending',
                 submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 processed_date TIMESTAMP,
                 processed_by TEXT,
                 FOREIGN KEY (farmer_id) REFERENCES farmers (id),
                 FOREIGN KEY (vendor_id) REFERENCES vendors (id),
                 FOREIGN KEY (equipment_id) REFERENCES equipment (id))''')
    
    conn_equipment.commit()
    conn_equipment.close()

init_db()




# ================= File Upload Config ==================
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ================= Routes ==================
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/userreg', methods=['GET', 'POST'])
def userreg():
    if request.method == 'POST':                                                                    
        full_name = request.form.get('full_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        farm_location = request.form.get('farm_location')
        farm_size = request.form.get('farm_size')
        crop_types = ','.join(request.form.getlist('crop_types'))
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        additional_info = request.form.get('additional_info')

        # File upload handling
        rtc_document = request.files.get('rtc_document')
        rtc_filename = None
        kannada_text = ""
        english_text = ""
        
        if rtc_document and rtc_document.filename:
            if allowed_file(rtc_document.filename):
                filename = secure_filename(rtc_document.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                rtc_document.save(filepath)
                rtc_filename = unique_filename
                
                # Extract text from the uploaded image
                kannada_text, english_text = extract_text_from_image(filepath)
            else:
                flash('Invalid file type for RTC document. Please upload PDF, JPG, or PNG files.', 'error')
                return render_template('userreg.html')

        # Password check
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('userreg.html')

        import re
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*])(?=.{8,})', password):
            flash('Password must have 8+ chars, uppercase, lowercase, number, special char.', 'error')
            return render_template('userreg.html')

        hashed_password = generate_password_hash(password)

        # Save to DB
        try:
            conn = sqlite3.connect('agriculture.db')
            c = conn.cursor()

            if email:
                c.execute("SELECT id FROM farmers WHERE email = ?", (email,))
                if c.fetchone():
                    flash('Email already registered!', 'error')
                    conn.close()
                    return render_template('userreg.html')

            c.execute('''INSERT INTO farmers 
                        (full_name, last_name, email, phone, farm_location, farm_size, 
                         crop_types, password, additional_info, rtc_document, kannada_text, english_text)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (full_name, last_name, email, phone, farm_location, farm_size,
                       crop_types, hashed_password, additional_info, rtc_filename, kannada_text, english_text))
            conn.commit()
            conn.close()

            # ✅ Send SMS after registration
            sms_message = "Thank you for registering with us! Your form is under process."
            send_sms(phone, sms_message)

            flash('Your farmer application has been submitted successfully! Please login.', 'success')
            return redirect(url_for('farmer_login'))

        except sqlite3.Error as e:
            flash(f'Error: {str(e)}', 'error')
            return render_template('userreg.html')

    return render_template('userreg.html')

# Route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# OCR endpoint for real-time processing
@app.route('/extract', methods=['POST'])
def extract():
    if 'image' not in request.files:
        return jsonify({"kannada": "", "english": ""}), 400

    f = request.files['image']
    
    if f.filename == '':
        return jsonify({"kannada": "", "english": ""}), 400
    
    # Save the file temporarily
    if f and allowed_file(f.filename):
        # Create a temporary file
        temp_filename = f"temp_{uuid.uuid4().hex}_{secure_filename(f.filename)}"
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        f.save(temp_filepath)
        
        # Extract text from the image
        kannada_text, english_text = extract_text_from_image(temp_filepath)
        
        # Delete the temporary file
        try:
            os.remove(temp_filepath)
        except:
            pass
        
        return jsonify({
            "kannada": kannada_text,
            "english": english_text
        })
    
    return jsonify({"kannada": "", "english": ""}), 400

# -------- Vendor Registration --------
@app.route('/vendorreg', methods=['GET', 'POST'])
def vendor_registration():
    if request.method == 'POST':
        # Get form data
        business_name = request.form.get('business_name')
        contact_name = request.form.get('contact_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        service_type = request.form.get('service_type')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        description = request.form.get('description')
        
        # Validate passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('vendorreg.html')
        
        # Validate password strength
        import re
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*])(?=.{8,})', password):
            flash('Password must be at least 8 characters with uppercase, lowercase, number, and special character', 'error')
            return render_template('vendorreg.html')
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        # Save to database
        try:
            conn = sqlite3.connect('vendors.db')
            c = conn.cursor()
            
            # Check if email already exists
            c.execute("SELECT id FROM vendors WHERE email = ?", (email,))
            if c.fetchone():
                flash('Email address already registered!', 'error')
                return render_template('vendorreg.html')
            
            # Insert new vendor
            c.execute('''INSERT INTO vendors 
                         (business_name, contact_name, email, phone, service_type, password, description)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (business_name, contact_name, email, phone, service_type, hashed_password, description))
            
            conn.commit()
            conn.close()
            
            flash('Your vendor application has been submitted successfully! Our team will review it shortly.', 'success')
            return redirect(url_for('vendor_login'))
            
        except sqlite3.Error as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('vendorreg.html')
    
    return render_template('vendorreg.html')

@app.route("/farmerlogin", methods=["GET", "POST"])
def farmer_login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        conn = sqlite3.connect('agriculture.db')
        c = conn.cursor()
        # Added status to the SELECT query
        c.execute("SELECT id, full_name, email, password, status FROM farmers WHERE email = ?", (email,))
        farmer = c.fetchone()
        conn.close()

        if farmer:
            # Check if password is correct
            if check_password_hash(farmer[3], password):
                # Check if farmer is approved
                if farmer[4] == 'approved':  # status is the 5th column (index 4)
                    session['user_id'] = farmer[0]
                    session['user_name'] = farmer[1]
                    session['user_email'] = farmer[2]
                    session['user_type'] = 'farmer'
                    flash('Login successful!', 'success')
                    return redirect(url_for("userdashboard"))
                else:
                    flash('Your account is pending approval by administrator', 'error')
            else:
                flash('Invalid email or password', 'error')
        else:
            flash('Invalid email or password', 'error')

    return render_template("farmer_login.html")

@app.route("/vendor_login", methods=["GET", "POST"])
def vendor_login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        conn = sqlite3.connect('vendors.db')
        c = conn.cursor()
        c.execute("SELECT id, business_name, email, password FROM vendors WHERE email = ?", (email,))
        vendor = c.fetchone()
        conn.close()

        if vendor and check_password_hash(vendor[3], password):
            session['vendor_id'] = vendor[0]
            session['vendor_name'] = vendor[1]
            session['vendor_email'] = vendor[2]
            session['user_type'] = 'vendor'
            flash('Login successful!', 'success')
            return redirect(url_for("dashboard"))  # this will go to /dashboard
        else:
            flash('Invalid email or password', 'error')

    return render_template("vendor_login.html")
# API endpoint to get equipment counts by category for vendor dashboard
@app.route('/api/vendor/equipment/counts')
def api_vendor_equipment_counts():
    if 'vendor_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    vendor_id = session['vendor_id']
    
    try:
        conn = sqlite3.connect('equipment.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Count equipment by category
        c.execute('''SELECT category, COUNT(*) as count 
                     FROM equipment 
                     WHERE vendor_id = ? 
                     GROUP BY category''', (vendor_id,))
        
        category_counts = c.fetchall()
        
        # Count total equipment
        c.execute('''SELECT COUNT(*) as total FROM equipment WHERE vendor_id = ?''', (vendor_id,))
        total_count = c.fetchone()[0]
        
        # Count available equipment
        c.execute('''SELECT COUNT(*) as available FROM equipment 
                     WHERE vendor_id = ? AND status = 'available' ''', (vendor_id,))
        available_count = c.fetchone()[0]
        
        # Count rented equipment
        c.execute('''SELECT COUNT(*) as rented FROM equipment 
                     WHERE vendor_id = ? AND status = 'rented' ''', (vendor_id,))
        rented_count = c.fetchone()[0]
        
        conn.close()
        
        # Format the response
        counts = {
            'total': total_count,
            'available': available_count,
            'rented': rented_count,
            'by_category': {}
        }
        
        for row in category_counts:
            counts['by_category'][row['category']] = row['count']
        
        return jsonify(counts)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to get vendor's equipment
@app.route('/api/vendor/equipment')
def api_vendor_equipment():
    if 'vendor_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    vendor_id = session['vendor_id']
    
    try:
        conn = sqlite3.connect('equipment.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''SELECT * FROM equipment WHERE vendor_id = ? ORDER BY created_date DESC''', (vendor_id,))
        equipment = c.fetchall()
        
        equipment_list = []
        for item in equipment:
            equipment_list.append({
                'id': item['id'],
                'name': item['name'],
                'category': item['category'],
                'description': item['description'],
                'price': item['price'],
                'price_unit': item['price_unit'],
                'location': item['location'],
                'status': item['status'],
                'image': item['image'],
                'created_date': item['created_date']
            })
        
        conn.close()
        return jsonify(equipment_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to add new equipment
@app.route('/api/vendor/equipment/add', methods=['POST'])
def api_add_equipment():
    if 'vendor_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    vendor_id = session['vendor_id']
    
    try:
        data = request.get_json()
        
        name = data.get('name')
        category = data.get('category')
        description = data.get('description')
        price = data.get('price')
        price_unit = data.get('price_unit')
        location = data.get('location')
        status = data.get('status', 'available')
        
        conn = sqlite3.connect('equipment.db')
        c = conn.cursor()
        
        c.execute('''INSERT INTO equipment 
                     (vendor_id, name, category, description, price, price_unit, location, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (vendor_id, name, category, description, price, price_unit, location, status))
        
        conn.commit()
        equipment_id = c.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'equipment_id': equipment_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to update equipment status (when rented/purchased)
@app.route('/api/vendor/equipment/<int:equipment_id>/status', methods=['PUT'])
def api_update_equipment_status(equipment_id):
    if 'vendor_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    vendor_id = session['vendor_id']
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        conn = sqlite3.connect('equipment.db')
        c = conn.cursor()
        
        # Verify the equipment belongs to this vendor
        c.execute('''SELECT id FROM equipment WHERE id = ? AND vendor_id = ?''', 
                  (equipment_id, vendor_id))
        
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Equipment not found'}), 404
        
        # Update status
        c.execute('''UPDATE equipment SET status = ? WHERE id = ?''', 
                  (new_status, equipment_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to create a booking
@app.route('/api/bookings/create', methods=['POST'])
def api_create_booking():
    if 'user_id' not in session or session.get('user_type') != 'farmer':
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session['user_id']
    
    try:
        data = request.get_json()
        
        equipment_id = data.get('equipment_id')
        vendor_id = data.get('vendor_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        total_amount = data.get('total_amount')
        
        conn = sqlite3.connect('equipment.db')
        c = conn.cursor()
        
        # Create booking
        c.execute('''INSERT INTO bookings 
                     (equipment_id, farmer_id, vendor_id, start_date, end_date, total_amount)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                     (equipment_id, farmer_id, vendor_id, start_date, end_date, total_amount))
        
        # Update equipment status to 'rented'
        c.execute('''UPDATE equipment SET status = 'rented' WHERE id = ?''', (equipment_id,))
        
        conn.commit()
        booking_id = c.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'booking_id': booking_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add this route for index.html
@app.route('/index.html')
def index_page():
    return render_template('index.html')

@app.route("/userdashboard")
def userdashboard():
   
    return render_template("userdashboard.html", user_name=session.get('user_name', 'User'))
@app.route("/vendordashboard")
def vendordashboard():
    if 'vendor_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('vendor_login'))
    
    # Get vendor details from database
    conn = sqlite3.connect('vendors.db')
    c = conn.cursor()
    c.execute("SELECT * FROM vendors WHERE id = ?", (session['vendor_id'],))
    vendor = c.fetchone()
    conn.close()
    
    return render_template("vendordashboard.html", 
                         vendor_id=session.get('vendor_id'),
                         vendor_name=session.get('vendor_name'),
                         vendor_email=session.get('vendor_email'))
# -------- Logout --------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))

# Admin credentials
ADMIN_EMAIL = "admin@lendahand.com"
ADMIN_PASSWORD = "admin123"

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check admin credentials
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_id'] = 1
            session['admin_name'] = 'Administrator'
            session['admin_email'] = ADMIN_EMAIL
            session['user_type'] = 'admin'
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password', 'error')
            
    return render_template('admin_login.html')

# Admin dashboard route (protected)
@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if admin is logged in
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Please log in as administrator first', 'error')
        return redirect(url_for('admin_login'))
    
    return render_template("admin_dashboard.html", admin_name=session.get('admin_name', 'Admin'))

# Admin logout route
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('user_type', None)
    flash('Admin logged out successfully', 'success')
    return redirect(url_for('admin_login'))

# API endpoint to get farmers data
@app.route('/api/admin/farmers')
def api_admin_farmers():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('agriculture.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get query parameters for filtering
    status_filter = request.args.get('status', 'all')
    search_term = request.args.get('search', '')
    
    query = "SELECT * FROM farmers"
    params = []
    
    # Apply filters if provided
    if status_filter != 'all' or search_term:
        query += " WHERE "
        conditions = []
        
        if status_filter != 'all':
            conditions.append("status = ?")
            params.append(status_filter)
            
        if search_term:
            conditions.append("(full_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ? OR farm_location LIKE ?)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
            
        query += " AND ".join(conditions)
    
    query += " ORDER BY registration_date DESC"
    
    c.execute(query, params)
    farmers = c.fetchall()
    
    # Convert to list of dictionaries
    farmers_list = []
    for farmer in farmers:
        farmers_list.append({
            'id': farmer['id'],
            'full_name': farmer['full_name'],
            'last_name': farmer['last_name'],
            'email': farmer['email'],
            'phone': farmer['phone'],
            'farm_location': farmer['farm_location'],
            'farm_size': farmer['farm_size'],
            'crop_types': farmer['crop_types'],
            'additional_info': farmer['additional_info'],
            'rtc_document': farmer['rtc_document'],
            'kannada_text': farmer['kannada_text'],
            'english_text': farmer['english_text'],
            'registration_date': farmer['registration_date'],
            'status': farmer['status']
        })
    
    conn.close()
    return jsonify(farmers_list)

# API endpoint to get vendors data
@app.route('/api/admin/vendors')
def api_admin_vendors():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('vendors.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get query parameters for filtering
    status_filter = request.args.get('status', 'all')
    search_term = request.args.get('search', '')
    
    query = "SELECT * FROM vendors"
    params = []
    
    # Apply filters if provided
    if status_filter != 'all' or search_term:
        query += " WHERE "
        conditions = []
        
        if status_filter != 'all':
            conditions.append("status = ?")
            params.append(status_filter)
            
        if search_term:
            conditions.append("(business_name LIKE ? OR contact_name LIKE ? OR email LIKE ? OR phone LIKE ? OR service_type LIKE ?)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
            
        query += " AND ".join(conditions)
    
    query += " ORDER BY registration_date DESC"
    
    c.execute(query, params)
    vendors = c.fetchall()
    
    # Convert to list of dictionaries
    vendors_list = []
    for vendor in vendors:
        vendors_list.append({
            'id': vendor['id'],
            'business_name': vendor['business_name'],
            'contact_name': vendor['contact_name'],
            'email': vendor['email'],
            'phone': vendor['phone'],
            'service_type': vendor['service_type'],
            'description': vendor['description'],
            'registration_date': vendor['registration_date'],
            'status': vendor['status']
        })
    
    conn.close()
    return jsonify(vendors_list)

# API endpoint to get dashboard statistics
@app.route('/api/admin/stats')
def api_admin_stats():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = {}
    
    # Get farmers stats
    conn_agri = sqlite3.connect('agriculture.db')
    c_agri = conn_agri.cursor()
    
    c_agri.execute("SELECT COUNT(*) FROM farmers")
    stats['total_farmers'] = c_agri.fetchone()[0]
    
    c_agri.execute("SELECT COUNT(*) FROM farmers WHERE status = 'pending'")
    stats['pending_farmers'] = c_agri.fetchone()[0]
    
    conn_agri.close()
    
    # Get vendors stats
    conn_vendors = sqlite3.connect('vendors.db')
    c_vendors = conn_vendors.cursor()
    
    c_vendors.execute("SELECT COUNT(*) FROM vendors")
    stats['total_vendors'] = c_vendors.fetchone()[0]
    
    c_vendors.execute("SELECT COUNT(*) FROM vendors WHERE status = 'pending'")
    stats['pending_vendors'] = c_vendors.fetchone()[0]
    
    conn_vendors.close()
    
    # These would come from other tables in a real application
    stats['total_equipment'] = 24
    stats['total_bookings'] = 156
    
    return jsonify(stats)

# API endpoint to approve a farmer
@app.route('/api/admin/farmer/approve/<int:farmer_id>', methods=['POST'])
def api_approve_farmer(farmer_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect('agriculture.db')
        c = conn.cursor()
        
        # Update farmer status to approved
        c.execute("UPDATE farmers SET status = 'approved' WHERE id = ?", (farmer_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to reject a farmer
@app.route('/api/admin/farmer/reject/<int:farmer_id>', methods=['POST'])
def api_reject_farmer(farmer_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect('agriculture.db')
        c = conn.cursor()
        
        # Get farmer phone number before updating
        c.execute("SELECT phone FROM farmers WHERE id = ?", (farmer_id,))
        farmer_phone = c.fetchone()
        
        if farmer_phone:
            # Send rejection SMS
            sms_message = "Your farmer registration has been rejected. Please contact support for more information."
            send_sms(farmer_phone[0], sms_message)
        
        c.execute("UPDATE farmers SET status = 'rejected' WHERE id = ?", (farmer_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to approve a vendor
@app.route('/api/admin/vendor/approve/<int:vendor_id>', methods=['POST'])
def api_approve_vendor(vendor_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect('vendors.db')
        c = conn.cursor()
        
        # Get vendor phone number before updating
        c.execute("SELECT phone FROM vendors WHERE id = ?", (vendor_id,))
        vendor_phone = c.fetchone()
        
        if vendor_phone:
            # Send approval SMS
            sms_message = "Your vendor registration has been approved! You can now access all features of the platform."
            send_sms(vendor_phone[0], sms_message)
        
        c.execute("UPDATE vendors SET status = 'approved' WHERE id = ?", (vendor_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to reject a vendor
@app.route('/api/admin/vendor/reject/<int:vendor_id>', methods=['POST'])
def api_reject_vendor(vendor_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect('vendors.db')
        c = conn.cursor()
        
        # Get vendor phone number before updating
        c.execute("SELECT phone FROM vendors WHERE id = ?", (vendor_id,))
        vendor_phone = c.fetchone()
        
        if vendor_phone:
            # Send rejection SMS
            sms_message = "Your vendor registration has been rejected. Please contact support for more information."
            send_sms(vendor_phone[0], sms_message)
        
        c.execute("UPDATE vendors SET status = 'rejected' WHERE id = ?", (vendor_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route("/translate")
def translate():
    response = httpx.get("https://example.com")  # ✅ sync request
    return response.text
# API endpoint to get bookings data
@app.route('/api/admin/bookings')
def api_admin_bookings():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    # In a real application, you would query from a bookings table
    # For now, let's create some sample data structure
    sample_bookings = [
        {
            'id': 1,
            'farmer_name': 'Rajesh Kumar',
            'vendor_name': 'AgriTech Solutions',
            'equipment_name': 'John Deere Tractor',
            'start_date': '2024-01-15',
            'end_date': '2024-01-20',
            'total_amount': 17500,
            'status': 'confirmed',
            'booking_date': '2024-01-10'
        },
        {
            'id': 2,
            'farmer_name': 'Priya Singh',
            'vendor_name': 'Farm Tools Co.',
            'equipment_name': 'Rotary Plough',
            'start_date': '2024-01-18',
            'end_date': '2024-01-22',
            'total_amount': 6000,
            'status': 'completed',
            'booking_date': '2024-01-12'
        },
        {
            'id': 3,
            'farmer_name': 'Amit Sharma',
            'vendor_name': 'AgriTech Solutions',
            'equipment_name': 'Combine Harvester',
            'start_date': '2024-01-25',
            'end_date': '2024-01-28',
            'total_amount': 36000,
            'status': 'pending',
            'booking_date': '2024-01-14'
        }
    ]
    
    # Get query parameters for filtering
    status_filter = request.args.get('status', 'all')
    search_term = request.args.get('search', '')
    
    # Apply filters
    filtered_bookings = sample_bookings
    
    if status_filter != 'all':
        filtered_bookings = [b for b in filtered_bookings if b['status'] == status_filter]
    
    if search_term:
        search_term = search_term.lower()
        filtered_bookings = [b for b in filtered_bookings if 
                           search_term in b['farmer_name'].lower() or 
                           search_term in b['vendor_name'].lower() or 
                           search_term in b['equipment_name'].lower()]
    
    return jsonify(filtered_bookings)
# Add this route to your Flask app
@app.route('/api/rent-requests', methods=['GET'])
def api_rent_requests():
    if 'vendor_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    vendor_id = session['vendor_id']
    
    try:
        conn = sqlite3.connect('equipment.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get rent requests for this vendor
        c.execute('''SELECT * FROM rent_requests 
                     WHERE vendor_id = ? 
                     ORDER BY submitted_date DESC''', (vendor_id,))
        
        requests = c.fetchall()
        
        requests_list = []
        for req in requests:
            requests_list.append({
                'id': req['id'],
                'farmer_name': req['farmer_name'],
                'farmer_phone': req['farmer_phone'],
                'equipment_name': req['equipment_name'],
                'start_date': req['start_date'],
                'end_date': req['end_date'],
                'duration': req['duration'],
                'purpose': req['purpose'],
                'notes': req['notes'],
                'total_amount': req['total_amount'],
                'status': req['status'],
                'submitted_date': req['submitted_date']
            })
        
        conn.close()
        return jsonify(requests_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rent-requests/<int:request_id>/<action>', methods=['POST'])
def api_update_rent_request(request_id, action):
    if 'vendor_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Invalid action'}), 400
    
    try:
        conn = sqlite3.connect('equipment.db')
        c = conn.cursor()
        
        # Verify the request belongs to this vendor
        c.execute('''SELECT * FROM rent_requests WHERE id = ? AND vendor_id = ?''', 
                  (request_id, session['vendor_id']))
        
        request_data = c.fetchone()
        if not request_data:
            conn.close()
            return jsonify({'error': 'Rent request not found'}), 404
        
        # Update request status
        new_status = 'approved' if action == 'approve' else 'rejected'
        c.execute('''UPDATE rent_requests 
                     SET status = ?, processed_date = CURRENT_TIMESTAMP, processed_by = ?
                     WHERE id = ?''', 
                  (new_status, session['vendor_name'], request_id))
        
        # If approved, update equipment status to rented
        if action == 'approve':
            c.execute('''UPDATE equipment SET status = 'rented' WHERE id = ?''', 
                      (request_data[3],))  # equipment_id is at index 3
        
        conn.commit()
        conn.close()
        
        # Send SMS notification to farmer
        farmer_phone = request_data[5]  # farmer_phone is at index 5
        status_text = "approved" if action == "approve" else "rejected"
        sms_message = f"Your rent request for {request_data[6]} has been {status_text} by the vendor."
        send_sms(farmer_phone, sms_message)
        
        return jsonify({'success': True, 'message': f'Rent request {status_text} successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# API endpoint to delete a booking
@app.route('/api/admin/booking/delete/<int:booking_id>', methods=['POST'])
def api_delete_booking(booking_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # In a real application, you would delete from the database
        # For now, we'll simulate deletion
        print(f"Booking {booking_id} would be deleted from database")
        
        return jsonify({'success': True, 'message': 'Booking deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoint to get booking details
@app.route('/api/admin/booking/<int:booking_id>')
def api_booking_details(booking_id):
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Sample booking details - in real app, query from database
    sample_booking = {
        'id': booking_id,
        'farmer_name': 'Rajesh Kumar',
        'farmer_phone': '+91 9876543210',
        'farmer_location': 'Bangalore Rural',
        'vendor_name': 'AgriTech Solutions',
        'vendor_phone': '+91 9876543211',
        'equipment_name': 'John Deere Tractor',
        'equipment_price': 3500,
        'start_date': '2024-01-15',
        'end_date': '2024-01-20',
        'total_days': 6,
        'total_amount': 21000,
        'service_fee': 2100,
        'final_amount': 23100,
        'status': 'confirmed',
        'booking_date': '2024-01-10',
        'special_requests': 'Need delivery to farm location',
        'payment_status': 'paid'
    }
    
    return jsonify(sample_booking)
@app.route('/api/vendor/profile')
def api_vendor_profile():
    if 'vendor_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    vendor_id = session['vendor_id']
    
    try:
        conn = sqlite3.connect('vendors.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT business_name, contact_name, email, phone, service_type, description FROM vendors WHERE id = ?", (vendor_id,))
        vendor = c.fetchone()
        conn.close()
        
        if vendor:
            return jsonify({
                'name': vendor['contact_name'],  # or vendor['business_name'] depending on what you want to display
                'business_name': vendor['business_name'],
                'email': vendor['email'],
                'phone': vendor['phone'],
                'service_type': vendor['service_type'],
                'description': vendor['description']
            })
        else:
            return jsonify({'error': 'Vendor not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# Add this route for farmers to submit rent requests
@app.route('/api/submit-rent-request', methods=['POST'])
def api_submit_rent_request():
    if 'user_id' not in session or session.get('user_type') != 'farmer':
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session['user_id']
    
    try:
        data = request.get_json()
        
        # Get farmer details
        conn_agri = sqlite3.connect('agriculture.db')
        c_agri = conn_agri.cursor()
        c_agri.execute("SELECT full_name, phone FROM farmers WHERE id = ?", (farmer_id,))
        farmer = c_agri.fetchone()
        conn_agri.close()
        
        if not farmer:
            return jsonify({'error': 'Farmer not found'}), 404
        
        # Get equipment details
        conn_equipment = sqlite3.connect('equipment.db')
        c_equipment = conn_equipment.cursor()
        c_equipment.execute('''SELECT e.*, v.id as vendor_id 
                              FROM equipment e 
                              JOIN vendors v ON e.vendor_id = v.id 
                              WHERE e.id = ?''', (data['equipment_id'],))
        equipment = c_equipment.fetchone()
        conn_equipment.close()
        
        if not equipment:
            return jsonify({'error': 'Equipment not found'}), 404
        
        # Calculate dates and amounts
        start_date = data['start_date']
        end_date = data['end_date']
        duration = data['duration']
        base_amount = equipment[4] * duration  # price * duration
        service_fee = base_amount * 0.1
        total_amount = base_amount + service_fee
        
        # Save rent request to database
        conn_equipment = sqlite3.connect('equipment.db')
        c_equipment = conn_equipment.cursor()
        
        c_equipment.execute('''INSERT INTO rent_requests 
                             (farmer_id, vendor_id, equipment_id, farmer_name, farmer_phone, 
                              equipment_name, start_date, end_date, duration, purpose, notes,
                              base_amount, service_fee, total_amount)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                             (farmer_id, equipment[8], data['equipment_id'], farmer[0], farmer[1],
                              equipment[1], start_date, end_date, duration, data['purpose'],
                              data.get('notes', ''), base_amount, service_fee, total_amount))
        
        conn_equipment.commit()
        request_id = c_equipment.lastrowid
        conn_equipment.close()
        
        # Send SMS notification to vendor
        vendor_conn = sqlite3.connect('vendors.db')
        vendor_c = vendor_conn.cursor()
        vendor_c.execute("SELECT phone FROM vendors WHERE id = ?", (equipment[8],))
        vendor_phone = vendor_c.fetchone()
        vendor_conn.close()
        
        if vendor_phone:
            sms_message = f"New rent request for {equipment[1]} from {farmer[0]}. Please check your dashboard."
            send_sms(vendor_phone[0], sms_message)
        
        return jsonify({'success': True, 'request_id': request_id})
        
    
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True)