from flask import Flask,render_template,request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import os


#2.creating the object of Flask class
app=Flask(__name__)  #values for constructor inside the class
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a strong key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



# DB and Login manager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



#load all the saved model
import pickle
with open("models/result_rf_model.pkl","rb")as f:
    rf_model=pickle.load(f)

with open("models/lb_education.pkl","rb")as f: 
    lb_education=pickle.load(f)

with open("models/lb_race.pkl","rb")as f:
    lb_race=pickle.load(f)  

#  Defining function
def predict_result(
    gender='male',
    race_ethnicity='group A',
    education='high school',
    math_score=80,
    reading_score=50,
    writing_score=50,
    lunch_free='standard',
    test_preparation='completed'
):
    lst = []

    # Gender encoding (assuming: female=0, male=1)
    if gender == 'female':
        lst.append(0)
    elif gender == 'male':
        lst.append(1)

    # Race/Ethnicity (encoded using label encoder)
    race_encoded = lb_race.transform([race_ethnicity])
    lst += list(race_encoded)
    

    # Education (use transform, not fit_transform)
    education_encoded = lb_education.transform([education])
    lst += list(education_encoded)

    # Numeric scores
    lst.append(math_score)
    lst.append(reading_score)
    lst.append(writing_score)

    # Lunch type (manual one-hot)
    if lunch_free == 'standard':
        lst += [1, 0]
    elif lunch_free == 'free/reduced':
        lst += [0, 1]

    # Test preparation (manual one-hot)
    if test_preparation == 'non':
        lst += [1, 0]
    elif test_preparation == 'completed':
        lst += [0, 1]

    # Prediction
    result = rf_model.predict([lst])
    return result[0]


#3.creating the route

# index
@app.route("/")  #@app.route("/",methods=['GET','POST']) #By default it takes 'GET'
@login_required
def index():
    return render_template("index.html")

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered.', 'warning')
            return redirect(url_for('register'))

        # Create new user
        new_user = User(email=email, password=generate_password_hash(password, method='pbkdf2:sha256'))

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route("/predict", methods=['GET', 'POST'])  
def predict():

 if request.method == 'POST':
    # Get student performance data from the form
    gender = request.form.get('gender')
    race_ethnicity = request.form.get('race_ethnicity')
    education = request.form.get('education')
    math_score = int(request.form.get('math_score'))
    reading_score = int(request.form.get('reading_score'))
    writing_score = int(request.form.get('writing_score'))
    lunch_free = request.form.get('lunch_free')
    test_preparation = request.form.get('test_preparation')

    # Optional: Print the values for debugging
    print(gender, race_ethnicity, education, math_score, reading_score, writing_score, lunch_free, test_preparation)

    # Use the predict_result function to get the prediction
    result = predict_result(
        gender=gender,
        race_ethnicity=race_ethnicity,
        education=education,
        math_score=math_score,
        reading_score=reading_score,
        writing_score=writing_score,
        lunch_free=lunch_free,
        test_preparation=test_preparation
    )

    # Pass the result to the template
    return render_template("predict.html", prediction=result)

 return render_template("predict.html")
    

if __name__=="__main__":
    with app.app_context():
        if not os.path.exists('users.db'):
            db.create_all()
    app.run(debug=True,port=4500)