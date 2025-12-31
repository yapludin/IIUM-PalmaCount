import os
import io
import json
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import firebase_admin
from firebase_admin import credentials, firestore, storage
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '0102490139')

# --- CONFIGURATION ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
FASTAPI_URL = os.environ.get('FASTAPI_URL', 'http://127.0.0.1:8000/api/predict')

# --- FIREBASE SETUP ---
# On Render/Production: 'FIREBASE_CREDENTIALS' env var contains the JSON string
# On Local: You can point to a file, or set the env var.
firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS')

if not firebase_admin._apps:
    try:
        if firebase_creds_json:
            # Handle Base64 encoded JSON if necessary (common in some CIs), or raw JSON string
            try:
                # Try parsing as raw JSON first
                cred_dict = json.loads(firebase_creds_json)
            except json.JSONDecodeError:
                # Try decoding base64
                decoded_json = base64.b64decode(firebase_creds_json).decode('utf-8')
                cred_dict = json.loads(decoded_json)
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': f"{cred_dict['project_id']}.firebasestorage.app" 
            })
            print("✅ Firebase Initialized from Environment Variable")
        else:
            # Local fallback (look for 'serviceAccountKey.json' in current dir)
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'palmacount.appspot.com' # Replace if you know your bucket name
            })
            print("✅ Firebase Initialized from Local File")
    except Exception as e:
        print(f"⚠️ Firebase Initialization Warning: {e}")

db = firestore.client()
bucket = storage.bucket()

# --- LOGIN MANAGER ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODELS (Wrapper for Firestore) ---
class User(UserMixin):
    def __init__(self, uid, email, fullname, password_hash):
        self.id = uid
        self.email = email
        self.fullname = fullname
        self.password_hash = password_hash

    @staticmethod
    def from_dict(uid, source):
        return User(
            uid=uid,
            email=source.get('email'),
            fullname=source.get('fullname'),
            password_hash=source.get('password_hash')
        )

@login_manager.user_loader
def load_user(user_id):
    doc_ref = db.collection('users').document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return User.from_dict(doc.id, doc.to_dict())
    return None

# --- FILTERS ---
@app.template_filter('kl_time')
def kl_time_filter(dt):
    if dt is None:
        return ""
    # Check if dt is a datetime object, if not try to parse
    if not isinstance(dt, datetime):
        # Firestore returns datetime with timezone info, usually UTC
        pass 
    
    # Simple conversion: UTC + 8 hours
    # In production with pytorch/timezone libraries it is more robust, but this works for basic needs
    # Assuming Firestore stores as UTC
    from datetime import timedelta
    return dt + timedelta(hours=8)

# --- ROUTES ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user exists
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1).stream()
        if any(query):
            flash('Email already registered!', 'danger')
            return redirect(url_for('signup'))
        
        hashed_pw = generate_password_hash(password, method='scrypt')
        
        # Add to Firestore
        new_user_ref = users_ref.document() # Auto-ID
        new_user_ref.set({
            'fullname': fullname,
            'email': email,
            'password_hash': hashed_pw,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html', current_page='signup')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        users_ref = db.collection('users')
        results = list(users_ref.where('email', '==', email).limit(1).stream())
        
        if results:
            user_doc = results[0]
            user_data = user_doc.to_dict()
            if check_password_hash(user_data['password_hash'], password):
                user_obj = User.from_dict(user_doc.id, user_data)
                login_user(user_obj)
                session['user_id'] = user_doc.id
                return redirect(url_for('dashboard'))
        
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', current_page='login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Fetch recent analyses
    analyses_ref = db.collection('analyses')
    query = analyses_ref.where('user_id', '==', current_user.id).order_by('created_at', direction=firestore.Query.DESCENDING).limit(5)
    recent_analyses = []
    for doc in query.stream():
        data = doc.to_dict()
        data['id'] = doc.id # Attach ID for linking
        recent_analyses.append(data)
    
    total_analyses = 0
    # Counting in NoSQL can be expensive, but acceptable for small scale
    # Better to store a counter on the User document, but query count is okay for MVP
    all_query = analyses_ref.where('user_id', '==', current_user.id).count() 
    # Note: aggregation queries might require an index, falling back to simple list for now if fails
    # Or just use len(list(analyses_ref.where...stream())) which is slow but safe for now.
    total_analyses = len(list(analyses_ref.where('user_id', '==', current_user.id).stream()))

    return render_template('dashboard.html', user=current_user, recent_analyses=recent_analyses, total_analyses=total_analyses)

@app.route('/history')
@login_required
def history():
    analyses_ref = db.collection('analyses')
    query = analyses_ref.where('user_id', '==', current_user.id).order_by('created_at', direction=firestore.Query.DESCENDING)
    all_analyses = []
    for doc in query.stream():
        data = doc.to_dict()
        data['id'] = doc.id
        all_analyses.append(data)
    
    return render_template('history.html', analyses=all_analyses)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # 1. Prepare File
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file_content = file.read()
                
                # 2. Send to Fast API (Backend)
                files = {'file': (filename, file_content, file.content_type)}
                response = requests.post(FASTAPI_URL, files=files, timeout=600)  # Long timeout
                
                if response.status_code == 200:
                    result = response.json()
                    tree_count = result.get('tree_count', 0)
                    processed_image_base64 = result.get('processed_image_base64')
                    confidence_score = result.get('confidence_score', 0.0)
                    
                    # 3. Upload Processed Image to Firebase Storage
                    image_data = base64.b64decode(processed_image_base64)
                    processed_filename = f"processed_{unique_filename}"
                    
                    blob = bucket.blob(f"analyses/{current_user.id}/{processed_filename}")
                    blob.upload_from_string(image_data, content_type='image/jpeg')
                    blob.make_public() # Make accessible via URL
                    image_url = blob.public_url
                    
                    # 4. Save Metadata to Firestore
                    doc_ref = db.collection('analyses').document()
                    doc_ref.set({
                        'user_id': current_user.id,
                        'original_filename': filename,
                        'processed_filename': image_url, # Now storing the Full URL
                        'tree_count': tree_count,
                        'confidence_score': confidence_score,
                        'created_at': firestore.SERVER_TIMESTAMP
                    })
                    
                    flash('Analysis successful!', 'success')
                    return redirect(url_for('analysis_detail', analysis_id=doc_ref.id))
                else:
                     flash(f'Error from AI Model: {response.text}', 'danger')
            
            except Exception as e:
                flash(f'An error occurred: {str(e)}', 'danger')
                
    return render_template('upload.html')

@app.route('/analysis/<analysis_id>')
@login_required
def analysis_detail(analysis_id):
    # Retrieve from Firestore
    doc_ref = db.collection('analyses').document(analysis_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        flash('Analysis not found', 'danger')
        return redirect(url_for('history'))
        
    analysis_data = doc.to_dict()
    analysis_data['id'] = doc.id
    
    # Check ownership
    if analysis_data.get('user_id') != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('history'))
    
    # The 'processed_filename' field now contains the full URL from Firebase Storage
    image_url = analysis_data.get('processed_filename')
    
    # Wrap data to look like an object for Jinja if needed, 
    # but Jinja can handle dicts if we used analysis.key syntax... 
    # Wait, existing templates use dot notation (analysis.tree_count).
    # We need a wrapper or update templates. Updating templates is safer but more work.
    # Let's use a wrapper class for 'Analysis' compatibility.
    
    class AnalysisWrapper:
        def __init__(self, data):
            self.id = data.get('id')
            self.original_filename = data.get('original_filename')
            self.processed_filename = data.get('processed_filename')
            self.tree_count = data.get('tree_count')
            self.confidence_score = data.get('confidence_score')
            self.created_at = data.get('created_at')
    
    analysis_obj = AnalysisWrapper(analysis_data)
        
    return render_template("analysis_detail.html", analysis=analysis_obj, processed_image_url=image_url)

@app.route('/delete_analysis/<analysis_id>', methods=['POST'])
@login_required
def delete_analysis(analysis_id):
    doc_ref = db.collection('analyses').document(analysis_id)
    doc = doc_ref.get()
    
    if doc.exists and doc.to_dict().get('user_id') == current_user.id:
        # Optional: Delete file from storage too to save space
        # file_url = doc.to_dict().get('processed_filename')
        # ... logic to parsing URL and deleting blob ...
        
        doc_ref.delete()
        flash('Analysis deleted successfully.', 'success')
    else:
        flash('Could not delete analysis.', 'danger')
        
    return redirect(url_for('history'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        new_password = request.form.get('password')
        
        updates = {}
        if fullname:
            updates['fullname'] = fullname
        
        if new_password:
            updates['password_hash'] = generate_password_hash(new_password, method='scrypt')
            
        if updates:
            db.collection('users').document(current_user.id).update(updates)
            flash('Profile updated successfully!', 'success')
            
            # Reload user in session
            updated_doc = db.collection('users').document(current_user.id).get()
            login_user(User.from_dict(updated_doc.id, updated_doc.to_dict()))
            
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=current_user)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)