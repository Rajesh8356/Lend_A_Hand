from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
import json
from datetime import datetime
import uuid
import httpx

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure random key

# ================= SMS Sending Function ==================
def send_sms(phone, message):
    url = "https://www.fast2sms.com/dev/bulkV2"

    payload = f"sender_id=LPOINT&message={message}&language=english&route=q&numbers={phone}"
    headers = {
        'Content-Type': "application/x-www-form-urlencoded",
        'Cache-Control': "no-cache",
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        print("SMS Response:", response.text)  # Debug output
        return response.json()
    except Exception as e:
        print("SMS Error:", str(e))
        return None

# ================= Database Initialization ==================
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

    # Agriculture database - Fixed table structure
    conn_agri = sqlite3.connect('agriculture.db')
    c_agri = conn_agri.cursor()
    
    c_agri.execute('''CREATE TABLE IF NOT EXISTS farmers
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             full_name TEXT NOT NULL,
             last_name TEXT NOT NULL,
             email TEXT UNIQUE,
             phone TEXT NOT NULL,
             farm_location TEXT NOT NULL,
             farm_size REAL,
             crop_types TEXT NOT NULL,
             password TEXT NOT NULL,
             additional_info TEXT,
             rtc_document TEXT,
             registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             status TEXT DEFAULT 'pending')''')
    conn_agri.commit()
    conn_agri.close()

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
        
        if rtc_document and rtc_document.filename:
            if allowed_file(rtc_document.filename):
                filename = secure_filename(rtc_document.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                rtc_document.save(filepath)
                rtc_filename = unique_filename
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

            # Check if email already exists
            if email:
                c.execute("SELECT id FROM farmers WHERE email = ?", (email,))
                if c.fetchone():
                    flash('Email already registered!', 'error')
                    conn.close()
                    return render_template('userreg.html')

            # Check if phone already exists
            c.execute("SELECT id FROM farmers WHERE phone = ?", (phone,))
            if c.fetchone():
                flash('Phone number already registered!', 'error')
                conn.close()
                return render_template('userreg.html')

            # Insert farmer data
            c.execute('''INSERT INTO farmers 
                        (full_name, last_name, email, phone, farm_location, farm_size, 
                         crop_types, password, additional_info, rtc_document)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (full_name, last_name, email, phone, farm_location, farm_size,
                       crop_types, hashed_password, additional_info, rtc_filename))
            conn.commit()
            conn.close()

            # ✅ Send SMS after registration
            sms_message = "Thank you for registering with us! Your farmer application is under review."
            sms_result = send_sms(phone, sms_message)
            
            # Display success message
            flash('Your farmer application has been submitted successfully! SMS notification sent.', 'success')
            return redirect(url_for('farmer_login'))

        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'error')
            return render_template('userreg.html')

    return render_template('userreg.html')

# Route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
                conn.close()
                return render_template('vendorreg.html')
            
            # Insert new vendor
            c.execute('''INSERT INTO vendors 
                         (business_name, contact_name, email, phone, service_type, password, description)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (business_name, contact_name, email, phone, service_type, hashed_password, description))
            
            conn.commit()
            conn.close()
            
            # Send SMS after vendor registration
            sms_message = "Thank you for registering as a vendor! Your application is under review."
            send_sms(phone, sms_message)
            
            flash('Your vendor application has been submitted successfully! SMS notification sent.', 'success')
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
        c.execute("SELECT id, full_name, email, password, status FROM farmers WHERE email = ?", (email,))
        farmer = c.fetchone()
        conn.close()

        if farmer:
            # Check if password is correct
            if check_password_hash(farmer[3], password):
                # Check if farmer is approved
                if farmer[4] == 'approved':
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
        c.execute("SELECT id, business_name, email, password, status FROM vendors WHERE email = ?", (email,))
        vendor = c.fetchone()
        conn.close()

        if vendor and check_password_hash(vendor[3], password):
            if vendor[4] == 'approved':
                session['vendor_id'] = vendor[0]
                session['vendor_name'] = vendor[1]
                session['vendor_email'] = vendor[2]
                session['user_type'] = 'vendor'
                flash('Login successful!', 'success')
                return redirect(url_for("vendordashboard"))
            else:
                flash('Your vendor account is pending approval by administrator', 'error')
        else:
            flash('Invalid email or password', 'error')

    return render_template("vendor_login.html")

@app.route('/index.html')
def index_page():
    return render_template('index.html')

@app.route("/userdashboard")
def userdashboard():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('farmer_login'))
    return render_template("userdashboard.html", user_name=session.get('user_name', 'User'))

@app.route("/vendordashboard")
def vendordashboard():
    if 'vendor_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('vendor_login'))
    return render_template("vendordashboard.html", vendor_name=session.get('vendor_name', 'Vendor'))

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

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        flash('Please log in as administrator first', 'error')
        return redirect(url_for('admin_login'))
    
    return render_template("admin_dashboard.html", admin_name=session.get('admin_name', 'Admin'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('user_type', None)
    flash('Admin logged out successfully', 'success')
    return redirect(url_for('admin_login'))

# API endpoint to get farmers data - FIXED
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
            conditions.append("(full_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ? OR farm_location LIKE ? OR crop_types LIKE ?)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
            
        query += " AND ".join(conditions)
    
    query += " ORDER BY registration_date DESC"
    
    c.execute(query, params)
    farmers = c.fetchall()
    
    # Convert to list of dictionaries - FIXED to match actual table structure
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
    
    status_filter = request.args.get('status', 'all')
    search_term = request.args.get('search', '')
    
    query = "SELECT * FROM vendors"
    params = []
    
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
    
    c_agri.execute("SELECT COUNT(*) FROM farmers WHERE status = 'approved'")
    stats['approved_farmers'] = c_agri.fetchone()[0]
    
    c_agri.execute("SELECT COUNT(*) FROM farmers WHERE status = 'rejected'")
    stats['rejected_farmers'] = c_agri.fetchone()[0]
    
    conn_agri.close()
    
    # Get vendors stats
    conn_vendors = sqlite3.connect('vendors.db')
    c_vendors = conn_vendors.cursor()
    
    c_vendors.execute("SELECT COUNT(*) FROM vendors")
    stats['total_vendors'] = c_vendors.fetchone()[0]
    
    c_vendors.execute("SELECT COUNT(*) FROM vendors WHERE status = 'pending'")
    stats['pending_vendors'] = c_vendors.fetchone()[0]
    
    c_vendors.execute("SELECT COUNT(*) FROM vendors WHERE status = 'approved'")
    stats['approved_vendors'] = c_vendors.fetchone()[0]
    
    c_vendors.execute("SELECT COUNT(*) FROM vendors WHERE status = 'rejected'")
    stats['rejected_vendors'] = c_vendors.fetchone()[0]
    
    conn_vendors.close()
    
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
        
        # Get farmer details before updating
        c.execute("SELECT phone, full_name FROM farmers WHERE id = ?", (farmer_id,))
        farmer_data = c.fetchone()
        
        if farmer_data:
            farmer_phone = farmer_data[0]
            farmer_name = farmer_data[1]
            
            # Send approval SMS
            sms_message = f"Dear {farmer_name}, your farmer registration has been approved! You can now login to access all features."
            send_sms(farmer_phone, sms_message)
        
        # Update farmer status to approved
        c.execute("UPDATE farmers SET status = 'approved' WHERE id = ?", (farmer_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Farmer approved successfully'})
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
        
        # Get farmer details before updating
        c.execute("SELECT phone, full_name FROM farmers WHERE id = ?", (farmer_id,))
        farmer_data = c.fetchone()
        
        if farmer_data:
            farmer_phone = farmer_data[0]
            farmer_name = farmer_data[1]
            
            # Send rejection SMS
            sms_message = f"Dear {farmer_name}, your farmer registration has been rejected. Please contact support for more information."
            send_sms(farmer_phone, sms_message)
        
        c.execute("UPDATE farmers SET status = 'rejected' WHERE id = ?", (farmer_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Farmer rejected successfully'})
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
        
        # Get vendor details before updating
        c.execute("SELECT phone, business_name FROM vendors WHERE id = ?", (vendor_id,))
        vendor_data = c.fetchone()
        
        if vendor_data:
            vendor_phone = vendor_data[0]
            vendor_name = vendor_data[1]
            
            # Send approval SMS
            sms_message = f"Dear {vendor_name}, your vendor registration has been approved! You can now login to access all features."
            send_sms(vendor_phone, sms_message)
        
        c.execute("UPDATE vendors SET status = 'approved' WHERE id = ?", (vendor_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Vendor approved successfully'})
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
        
        # Get vendor details before updating
        c.execute("SELECT phone, business_name FROM vendors WHERE id = ?", (vendor_id,))
        vendor_data = c.fetchone()
        
        if vendor_data:
            vendor_phone = vendor_data[0]
            vendor_name = vendor_data[1]
            
            # Send rejection SMS
            sms_message = f"Dear {vendor_name}, your vendor registration has been rejected. Please contact support for more information."
            send_sms(vendor_phone, sms_message)
        
        c.execute("UPDATE vendors SET status = 'rejected' WHERE id = ?", (vendor_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Vendor rejected successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)