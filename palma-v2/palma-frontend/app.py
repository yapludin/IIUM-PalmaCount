import os
import requests
import base64
from flask import Flask, render_template, request, redirect, url_for, flash, session
from firebase_config import auth

app = Flask(__name__)
app.secret_key = "0102490139"

# --- CLOUD CONFIGURATION ---
# Default to localhost for testing, but check Environment Variable for Cloud URL
# When you deploy to Render, you will set 'FASTAPI_URL' in the Render Dashboard
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://127.0.0.1:8000/api/predict")

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    image_base64 = None

    if request.method == "POST":
        file = request.files.get("image")
        if file:
            try:
                # Send image to FastAPI
                response = requests.post(
                    FASTAPI_URL,
                    files={"image": (file.filename, file, file.content_type)}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data
                    # Pass Base64 directly to template (No saving to disk!)
                    image_base64 = data.get("image_base64")
                else:
                    flash(f"Error from AI Backend: {response.status_code}")
            except requests.exceptions.ConnectionError:
                flash("Could not connect to AI Backend. Is it running?")

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
    
    user = session["user"]
    
    # --- MOCK DATA (Replace with Database calls later) ---
    # This simulates the "Activity Overview" & "User Statistics"
    user_stats = {
        "total_scans": 12,
        "total_trees_counted": 1450,
        "account_type": "Researcher",
        "member_since": "Dec 2024",
        "badge": "Forest Guardian"
    }
    
    recent_history = [
        {"id": 101, "date": "07 Dec 2025", "filename": "site_A_drone.jpg", "trees": 120, "status": "Completed"},
        {"id": 102, "date": "06 Dec 2025", "filename": "gombak_sector_2.jpg", "trees": 85, "status": "Completed"},
        {"id": 103, "date": "01 Dec 2025", "filename": "test_image_01.png", "trees": 0, "status": "Failed"},
    ]
    
    return render_template('profile.html', user=user, stats=user_stats, history=recent_history)

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
    if request.method == 'POST':
        if 'image' not in request.files:
            return "No image uploaded", 400
            
        file = request.files['image']
        
        # Prepare files for request
        # We send the file object directly to the backend
        files_to_send = {'image': (file.filename, file, file.mimetype)}

        try:
            response = requests.post(FASTAPI_URL, files=files_to_send)
            
            if response.status_code != 200:
                 flash(f"Backend Error: {response.text}")
                 return redirect(url_for('upload'))
                 
            data = response.json()

            if data.get("status") == "success":
                # --- CRITICAL FIX ---
                # 1. We do NOT save to static/output.jpg (Cloud servers wipe this folder)
                # 2. We pass the whole 'data' object so results.html can see the Charts & Areas
                
                return render_template(
                    "results.html", 
                    result=data, 
                    image_base64=data.get("image_base64")
                )

        except Exception as e:
            flash(f"Error processing image: {str(e)}")
            return redirect(url_for('upload'))

    return render_template("upload.html")

@app.route('/results')
def results():
    # This route is mostly for history, as the actual results are shown 
    # immediately after the POST request in /upload
    if "user" not in session:
        return redirect(url_for('login'))
    user = session['user']
    return render_template('results.html', user=user)

@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect('/login')

@app.context_processor
def inject_user():
    return dict(user=session.get("user"))

if __name__ == "__main__":
    # Gunicorn will handle the port in production, this is for local testing
    app.run(debug=True, port=5500)