from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from firebase_config import auth
import requests
import base64
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "0102490139"

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analyses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

FASTAPI_URL = "http://127.0.0.1:8000/api/predict"

# Database Model
class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.String(100), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    processed_filename = db.Column(db.String(200), nullable=False)
    mature_count = db.Column(db.Integer, nullable=False)
    young_count = db.Column(db.Integer, nullable=False)
    total_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Analysis {self.analysis_id}>'

# Create database tables
with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def index():
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next')

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = user
            return redirect(next_page or url_for('dashboard'))

        except:
            flash("Invalid credentials")
            return redirect('/login')

    return render_template('login.html', next_page=next_page)

@app.route('/profile')
def profile():
    if "user" not in session:
        return redirect(url_for('login'))
    
    user = session['user']
    user_id = user['localId']
    
    # Get user's analyses from database
    user_analyses = Analysis.query.filter_by(user_id=user_id).all()
    
    # Calculate stats
    total_scans = len(user_analyses)
    total_trees_counted = sum(analysis.total_count for analysis in user_analyses)
    
    # Determine badge based on scans
    if total_scans >= 50:
        badge = "Palm Master 🌴"
    elif total_scans >= 20:
        badge = "Tree Expert 🌳"
    elif total_scans >= 10:
        badge = "Sapling Scout 🌱"
    elif total_scans >= 5:
        badge = "Seedling Starter 🌿"
    else:
        badge = "New Planter 🪴"
    
    # Prepare stats dictionary
    stats = {
        'total_scans': total_scans,
        'total_trees_counted': total_trees_counted,
        'account_type': 'Premium User' if total_scans > 10 else 'Free User',
        'badge': badge,
        'mature_total': sum(analysis.mature_count for analysis in user_analyses),
        'young_total': sum(analysis.young_count for analysis in user_analyses),
        'analyses': user_analyses[:5]  # Last 5 analyses for recent scans
    }
    
    return render_template('profile.html', user=user, stats=stats)

@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect('/login')

    user = session["user"]
    return render_template('dashboard.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.create_user_with_email_and_password(email, password)
            session['user'] = user
            return redirect('/dashboard')
        except Exception as e:
            flash("Registration failed: " + str(e))
            return redirect('/register')

    return render_template('register.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if "user" not in session:
        return redirect(url_for('login', next=url_for('upload')))
    
    if request.method == 'POST':
        file = request.files['image']
        
        # Generate unique IDs for this analysis
        analysis_id = str(uuid.uuid4())[:8]
        original_filename = file.filename
        processed_filename = f"{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        # Save original file temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{processed_filename}")
        file.save(temp_path)
        
        # Send image to FastAPI
        with open(temp_path, 'rb') as f:
            files = {'image': (file.filename, f, file.mimetype)}
            response = requests.post(FASTAPI_URL, files=files)
        
        # Remove temp file
        os.remove(temp_path)
        
        data = response.json()

        if data["status"] == "success":
            # Save processed image with unique name
            image_data = base64.b64decode(data["image_base64"])
            processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
            with open(processed_path, "wb") as f:
                f.write(image_data)
            
            # Save analysis to database
            new_analysis = Analysis(
                analysis_id=analysis_id,
                user_id=session['user']['localId'],
                original_filename=original_filename,
                processed_filename=processed_filename,
                mature_count=data["total_mature"],
                young_count=data["total_young"],
                total_count=data["total_oil_palms"]
            )
            
            db.session.add(new_analysis)
            db.session.commit()
            
            # Store analysis_id in session for immediate viewing
            session['last_analysis_id'] = analysis_id
            
            # Redirect to results page with analysis ID
            return redirect(url_for('analysis_detail', analysis_id=analysis_id))

        return "Analysis failed", 500

    return render_template("upload.html")

@app.route('/results')
def results():
    if "user" not in session:
        return redirect(url_for('login'))

    user = session['user']
    uploaded_file_name = session.get('uploaded_file_name')
    
    return render_template('results.html', user=user, uploaded_file_name=uploaded_file_name)

@app.route('/analysis/<analysis_id>')
def analysis_detail(analysis_id):
    if "user" not in session:
        return redirect(url_for('login'))
    
    # Get analysis from database
    analysis = Analysis.query.filter_by(analysis_id=analysis_id, user_id=session['user']['localId']).first()
    
    if not analysis:
        flash("Analysis not found")
        return redirect(url_for('history'))
    
    totals = {
        "mature": analysis.mature_count,
        "young": analysis.young_count,
        "total": analysis.total_count
    }
    
    return render_template("analysis_detail.html", 
                         totals=totals, 
                         analysis=analysis,
                         processed_image_url=url_for('static', filename=f'processed/{analysis.processed_filename}'))

@app.route('/history')
def history():
    if "user" not in session:
        return redirect(url_for('login'))
    
    # Get all analyses for current user, ordered by most recent first
    analyses = Analysis.query.filter_by(user_id=session['user']['localId'])\
                             .order_by(Analysis.created_at.desc())\
                             .all()
    
    return render_template('history.html', analyses=analyses)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect('/login')

@app.context_processor
def inject_user():
    return dict(user=session.get("user"))

if __name__ == "__main__":
    app.run(debug=True, port=5500)