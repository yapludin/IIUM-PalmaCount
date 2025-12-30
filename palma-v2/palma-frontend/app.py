from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import requests
import base64
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "0102490139"

# --- Database configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analyses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

FASTAPI_URL = "http://127.0.0.1:8000/api/predict"

# --- Database Models ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    processed_filename = db.Column(db.String(200), nullable=False)
    mature_count = db.Column(db.Integer, nullable=False)
    young_count = db.Column(db.Integer, nullable=False)
    total_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref='analyses')

# Initialize Database
with app.app_context():
    db.create_all()

# --- Context Processor (Makes 'current_user' available in all HTML) ---
@app.context_processor
def inject_user():
    # We call it 'user_data' to be 100% sure it doesn't clash with the 'User' class
    user_data = None
    if 'user_id' in session:
        user_data = User.query.get(session['user_id'])
    return dict(user=user_data)


# --- Routes ---

@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" in session:
        return redirect(url_for('dashboard'))

    result = None
    image_base64 = None

    if request.method == "POST":
        file = request.files.get("image")
        if file:
            response = requests.post(
                FASTAPI_URL,
                files={"image": (file.filename, file, file.content_type)}
            )
            if response.status_code == 200:
                data = response.json()
                result = data
                image_base64 = data["image_base64"]

    return render_template("index.html", result=result, image_base64=image_base64)
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')  # Captured from your HTML form
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')

        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for('register'))

        # Create user with the name argument
        new_user = User(name=name, email=email) 
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        return redirect(url_for('dashboard'))

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
def dashboard():
    if "user_id" not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files['image']
        analysis_id = str(uuid.uuid4())[:8]
        processed_filename = f"{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{processed_filename}")
        file.save(temp_path)
        
        with open(temp_path, 'rb') as f:
            files = {'image': (file.filename, f, file.mimetype)}
            response = requests.post(FASTAPI_URL, files=files)
        
        os.remove(temp_path)
        data = response.json()

        if data.get("status") == "success":
            image_data = base64.b64decode(data["image_base64"])
            processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
            with open(processed_path, "wb") as f:
                f.write(image_data)
            
            new_analysis = Analysis(
                analysis_id=analysis_id,
                user_id=session['user_id'],
                original_filename=file.filename,
                processed_filename=processed_filename,
                mature_count=data["total_mature"],
                young_count=data["total_young"],
                total_count=data["total_oil_palms"]
            )
            db.session.add(new_analysis)
            db.session.commit()
            return redirect(url_for('analysis_detail', analysis_id=analysis_id))

        flash("Analysis failed")
        return redirect(url_for('upload'))

    return render_template("upload.html")

@app.route('/profile')
def profile():
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    user_analyses = Analysis.query.filter_by(user_id=user.id).all()
    
    total_scans = len(user_analyses)
    total_trees = sum(a.total_count for a in user_analyses)
    
    # Badge Logic
    badge = "New Planter 🪴"
    if total_scans >= 50: badge = "Palm Master 🌴"
    elif total_scans >= 20: badge = "Tree Expert 🌳"
    elif total_scans >= 10: badge = "Sapling Scout 🌱"

    stats = {
        'total_scans': total_scans,
        'total_trees_counted': total_trees,
        'badge': badge,
        'analyses': user_analyses[-5:]
    }
    return render_template('profile.html', user=user, stats=stats)

@app.route('/history')
def history():
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    analyses = Analysis.query.filter_by(user_id=session['user_id'])\
                             .order_by(Analysis.created_at.desc()).all()
    return render_template('history.html', analyses=analyses)

@app.route('/analysis/<analysis_id>')
def analysis_detail(analysis_id):
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    # Get analysis from database
    analysis = Analysis.query.filter_by(analysis_id=analysis_id, user_id=session['user_id']).first()
    
    if not analysis:
        flash("Analysis not found")
        return redirect(url_for('history'))
    
    # Generate the image URL manually here
    image_url = url_for('static', filename='processed/' + analysis.processed_filename)
    
    return render_template("analysis_detail.html", 
                           analysis=analysis,
                           processed_image_url=image_url)

@app.route('/about')  # This defines the URL (e.g., localhost:5000/about)
def about():
    return render_template('about.html') # This must match your filename exactly

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, port=5500)