from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
import base64
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = "0102490139"

# --- Configuration ---
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///analyses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'

# Ensure directories exist
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'pfps'), exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://127.0.0.1:8000/api/predict")

# --- Database Models ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False) # Original name field
    full_name = db.Column(db.String(100))            # New field for profile editing
    profile_pic = db.Column(db.String(255))         # Stores URL or file path
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def tier(self):
        scan_count = len(self.analyses)
        if scan_count >= 20:
            return "Palm Master 🌴"
        elif scan_count >= 10:
            return "Tree Expert 🌳"
        elif scan_count >= 5:
            return "Sapling Scout 🌱"
        return "New Planter 🪴"

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    processed_filename = db.Column(db.String(200), nullable=False)
    mature_count = db.Column(db.Integer, nullable=False)
    young_count = db.Column(db.Integer, nullable=False)
    total_count = db.Column(db.Integer, nullable=False)

    total_area_m2 = db.Column(db.Float, nullable=True, default=0.0)
    total_area_ha = db.Column(db.Float, nullable=True, default=0.0)
    confidence = db.Column(db.Float, nullable=True, default=0.0)
    method_name = db.Column(db.String(100), nullable=True)
    chart_base64 = db.Column(db.Text, nullable=True) # Text stores long Base64 strings

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    custom_name = db.Column(db.String(100), nullable=True)
    user = db.relationship('User', backref='analyses')

# Initialize Database
with app.app_context():
    db.create_all()

# --- Context Processor ---
@app.context_processor
def inject_user():
    user_data = None
    if 'user_id' in session:
        user_data = User.query.get(session['user_id'])
    return dict(user=user_data)

# --- Authentication Wrapper (Replaces @login_required) ---
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" in session:
        return redirect(url_for('dashboard'))
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password') # Capture the second password

        # 1. Check if all fields are present
        if not name or not email or not password:
            flash("All fields are required")
            return redirect(url_for('register'))

        # 2. Server-side password match check (CRITICAL)
        if password != confirm_password:
            flash("Passwords do not match")
            return redirect(url_for('register'))

        # 3. Server-side length check
        if len(password) < 8:
            flash("Password must be at least 8 characters long")
            return redirect(url_for('register'))

        # 4. Check if user exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for('register'))

        # 5. Create user
        try:
            new_user = User(name=name, full_name=name, email=email) 
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash("Invalid credentials")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['image']
        
        # --- 1. Generate Unique Internal ID (Safe for URL/DB) ---
        analysis_id = str(random.randint(10000000, 99999999))
        
        # --- 2. Generate Friendly Sequential Name (YYMMDD_NNN) ---
        today_obj = datetime.now() 
        today_str = today_obj.strftime('%y%m%d')
        
        # FIX: Database stores UTC (datetime.utcnow), so strict date filtering might miss recent uploads.
        # Instead, we just look for ANY analysis with this user that matches the pattern "YYMMDD_%"
        # This is more robust than date filtering.
        existing_names = Analysis.query.filter(
            Analysis.user_id == session['user_id'],
            Analysis.custom_name.like(f"{today_str}_%") 
        ).with_entities(Analysis.custom_name).all()
        
        max_seq = 0
        for (name,) in existing_names:
            try:
                # Extract "001" from "260103_001"
                suffix = int(name.split('_')[-1])
                if suffix > max_seq:
                    max_seq = suffix
            except (ValueError, IndexError):
                continue
                    
        sequence_num = max_seq + 1
        friendly_name = f"{today_str}_{sequence_num:03d}"
        
        # --- 3. Filename uses UNIQUE ID to prevent overwrites ---
        processed_filename = f"{analysis_id}_{datetime.now().strftime('%H%M%S')}.jpg"
        
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{processed_filename}")
        file.save(temp_path)
        
        try:
            with open(temp_path, 'rb') as f:
                files = {'image': (file.filename, f, file.mimetype)}
                response = requests.post(FASTAPI_URL, files=files, timeout=60) # Add timeout
            
            os.remove(temp_path)
            
            # Check for HTTP errors (4xx, 5xx)
            if response.status_code != 200:
                try:
                    error_detail = response.json().get('detail', 'Unknown backend error')
                except:
                    error_detail = f"Server returned {response.status_code}"
                flash(f"Analysis failed: {error_detail}", "danger")
                return redirect(url_for('upload'))
                
            data = response.json()

            if data.get("status") == "success":
                # 1. Access the nested 'analysis' object from FastAPI
                analysis_results = data.get("analysis", {})
                
                # --- GUARDRAIL: REJECT ZERO TREES ---
                # If the model finds nothing, there is no point saving it.
                if analysis_results.get("total_count", 0) == 0:
                    flash("Analysis rejected: No valid palm trees detected. Please upload a clear aerial image containing trees.", "danger")
                    return redirect(url_for('upload'))
                
                # 2. Extract and Save the Processed Image
                image_base64 = analysis_results.get("image_base64")
                if image_base64:
                    image_data = base64.b64decode(image_base64)
                    processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
                    with open(processed_path, "wb") as f:
                        f.write(image_data)
                
                # 3. Save to Database
                new_analysis = Analysis(
                    analysis_id=analysis_id,
                    user_id=session['user_id'],
                    original_filename=file.filename,
                    processed_filename=processed_filename,
                    
                    # USER SEES THIS: "260103_001", "260103_002"
                    custom_name=friendly_name, 
                    
                    # Tree Counts
                    mature_count=analysis_results.get("mature_count", 0),
                    young_count=analysis_results.get("young_count", 0),
                    total_count=analysis_results.get("total_count", 0),
                    
                    # Area Metrics
                    total_area_m2=analysis_results.get("total_area_m2", 0),
                    total_area_ha=analysis_results.get("total_area_ha", 0),
                    confidence=analysis_results.get("confidence", 0.0),
                    method_name=analysis_results.get("method_name", "Owen & Lines (2024)"),
                    
                    # Chart Data
                    chart_base64=analysis_results.get("chart_base64")
                )
                
                db.session.add(new_analysis)
                db.session.commit()
                
                return redirect(url_for('analysis_detail', analysis_id=analysis_id))
            
            else:
                # Backend returned 200 but status != success (custom logic error)
                flash(f"Analysis Error: {data.get('message', 'Unknown processing error')}", "danger")
                
        except requests.exceptions.RequestException as e:
            flash(f"Connection Error: Could not reach analysis server. Is it running?", "danger")
            # If temp file still exists in case of crash before remove
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
    return render_template("upload.html")



# Add this route to your app.py
@app.route('/delete_analysis/<analysis_id>', methods=['POST'])
@login_required
def delete_analysis(analysis_id):
    # 1. Fetch the analysis using session['user_id'] for security
    analysis = Analysis.query.filter_by(analysis_id=analysis_id, user_id=session['user_id']).first_or_404()
    
    # 2. Delete the actual image file to save space
    try:
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], analysis.processed_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")

    # 3. Delete from Database (This automatically removes it from Dashboard & History)
    db.session.delete(analysis)
    db.session.commit()

    flash('Analysis record deleted successfully.', 'success')
    
    # Redirect back to the page they came from, or default to history
    return redirect(url_for('history'))

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    user_analyses = Analysis.query.filter_by(user_id=user.id).all()
    
    total_scans = len(user_analyses)
    total_trees = sum(a.total_count for a in user_analyses)

    stats = {
        'total_scans': total_scans,
        'total_trees_counted': total_trees,
        'badge': user.tier,
        'analyses': user_analyses[-5:],
        'account_type': 'Premium Member' if total_scans > 10 else 'Basic Member'
    }
    return render_template('profile.html', user=user, stats=stats)

# ... inside app.py ...

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = User.query.get(session['user_id'])
    
    # 1. Get data from the form inputs
    full_name = request.form.get('full_name', '').strip()
    nickname = request.form.get('nickname', '').strip()
    
    # 2. Update Database Fields
    if full_name:
        user.full_name = full_name
        
    # We use 'nickname' as the primary 'name' (or creating separate columns if your DB has them)
    if nickname:
        user.name = nickname # This updates the user.name used in some greetings
        
    # Password logic (kept same as before)
    new_pwd = request.form.get('new_password')
    confirm_pwd = request.form.get('confirm_password')
    
    if new_pwd:
        if new_pwd == confirm_pwd:
            user.set_password(new_pwd)
        else:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('profile'))

    db.session.commit()
    flash("Profile updated successfully!", "success")
    return redirect(url_for('profile'))

@app.route('/upload_pfp', methods=['POST'])
@login_required
def upload_pfp():
    if 'pfp_file' in request.files:
        file = request.files['pfp_file']
        if file and file.filename != '':
            pfp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'pfps')
            
            # 1. Generate a unique filename using timestamp to prevent browser caching
            # e.g., user_1_20231025120000.jpg
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = secure_filename(f"user_{session['user_id']}_{timestamp}.jpg")
            
            # Save file
            file.save(os.path.join(pfp_dir, filename))
            
            # 2. Update DB with the new path
            user = User.query.get(session['user_id'])
            user.profile_pic = url_for('static', filename=f'uploads/pfps/{filename}')
            
            db.session.commit()
            flash("Profile picture updated!", "success")
            
    return redirect(url_for('profile'))

@app.route('/set_icon_pfp', methods=['POST'])
@login_required
def set_icon_pfp():
    icon_name = request.form.get('icon_name')
    user = User.query.get(session['user_id'])
    user.profile_pic = f"https://ui-avatars.com/api/?name={icon_name}&background=15803d&color=fff&size=128"
    db.session.commit()
    flash("Profile icon updated!", "success")
    return redirect(url_for('profile'))

@app.route('/history')
@login_required
def history():
    analyses = Analysis.query.filter_by(user_id=session['user_id'])\
                             .order_by(Analysis.created_at.desc()).all()
    return render_template('history.html', analyses=analyses)

@app.route('/analysis/<analysis_id>')
@login_required
def analysis_detail(analysis_id):
    analysis = Analysis.query.filter_by(analysis_id=analysis_id, user_id=session['user_id']).first_or_404()
    image_url = url_for('static', filename='processed/' + analysis.processed_filename)
    return render_template("analysis_detail.html", analysis=analysis, processed_image_url=image_url)

@app.route('/about')  

def about():

    return render_template('about.html') 

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Template Filters ---
@app.template_filter('kl_time')
def kl_time_filter(dt):
    if dt is None:
        return ""
    # Add 8 hours to the database UTC time
    return dt + timedelta(hours=8)



if __name__ == "__main__":
    app.run(debug=True, port=5500)