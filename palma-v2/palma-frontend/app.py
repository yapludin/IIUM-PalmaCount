from flask import Flask, render_template, request, redirect, url_for, flash, session
from firebase_config import auth
import requests
import base64

app = Flask(__name__)

FASTAPI_URL = "http://127.0.0.1:8000/api/predict"

app = Flask(__name__)
app.secret_key = "0102490139" 


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
    next_page = request.args.get('next')  # page user originally wanted

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = user

            # redirect to the original page if exists, otherwise dashboard
            return redirect(next_page or url_for('dashboard'))

        except:
            flash("Invalid credentials")
            return redirect('/login')

    return render_template('login.html', next_page=next_page)

@app.route('/profile')
def profile ():
    return render_template('profile.html')


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
        file = request.files['image']
        files = {'image': (file.filename, file.stream, file.mimetype)}

        # Send image to FastAPI
        response = requests.post(FASTAPI_URL, files=files)
        data = response.json()

        if data["status"] == "success":
            counts = {
                "mature": data["total_mature"],
                "young": data["total_young"],
                "total": data["total_oil_palms"]
            }

            # Save processed image from base64 to static folder
            image_data = base64.b64decode(data["image_base64"])
            with open("static/output.jpg", "wb") as f:
                f.write(image_data)

            return render_template("results.html", totals=counts)

        return "Analysis failed", 500

    return render_template("upload.html")


@app.route('/results')
def results():
    if "user" not in session:
        return redirect(url_for('login'))

    user = session['user']
    uploaded_file_name = session.get('uploaded_file_name')  # get any data you want to show

    # Render result page, pass user + analysis results
    return render_template('results.html', user=user, uploaded_file_name=uploaded_file_name)


@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect('/login')


@app.context_processor
def inject_user():
    return dict(user=session.get("user"))


if __name__ == "__main__":
    app.run(debug=True, port=5500)
