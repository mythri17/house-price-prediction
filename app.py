from flask import Flask, render_template, request, redirect, session
import pickle
import pandas as pd
import numpy as np
import sqlite3
import traceback
from flask_mail import Mail, Message

# ---------------- APP ----------------
app = Flask(__name__)
app.secret_key = "secret123"
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'predictionsystem17@gmail.com'
app.config['MAIL_PASSWORD'] = 'ikhmtaqjrjzfuvzr'
mail = Mail(app)
@app.route('/test-email')
def test_email():

    msg = Message(
        subject='Test Email',
        sender='predictionsystem17@gmail.com',
        recipients=['mythri1717@gmail.com']
    )

    msg.body = "This is a test email from House Price Prediction."

    try:
        mail.send(msg)
        return "Email Sent Successfully"
    except Exception as e:
        return f"Email Error: {e}"

# ---------------- DB CONNECTION ----------------

conn = sqlite3.connect("house.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT,
    sqft REAL,
    bhk INTEGER,
    bath INTEGER,
    price REAL
)
""")

conn.commit()
print("SQLite Connected Successfully")


# ---------------- LOAD MODEL ----------------
model = pickle.load(open('model.pkl', 'rb'))
columns = list(pickle.load(open('columns.pkl', 'rb')))

# ---------------- LOCATIONS ----------------
AREAS = sorted([
    col.replace('location_', '')
    for col in columns
    if col.startswith('location_')
])

# ---------------- FORMAT INDIAN CURRENCY ----------------
def format_indian_currency(num):

    num = int(num)

    s = str(num)

    last3 = s[-3:]

    rest = s[:-3]

    if rest != '':

        rest = rest[::-1]

        parts = [
            rest[i:i+2]
            for i in range(0, len(rest), 2)
        ]

        rest = ','.join(parts)[::-1]

        return rest + ',' + last3

    else:
        return last3


# ---------------- VALIDATION ----------------
def validate_inputs(sqft, bhk, bath):

    if sqft < 1000 or sqft > 5000:
        return "❌ Sqft must be between 1000 - 5000"

    if bhk < 1 or bhk > 8:
        return "❌ BHK must be between 1 - 8"

    if bath < 1 or bath > 6:
        return "❌ Bathrooms must be between 1 - 6"

    return "OK"


# ---------------- LOGIN ----------------
import re

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Username validation
        if len(username) < 4:
            return render_template(
                'login.html',
                error='Username must be at least 4 characters'
            )

        # Email validation
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(email_pattern, email):
            return render_template(
                'login.html',
                error='Please enter a valid email address'
            )

        # Password validation
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'

        if not re.match(pattern, password):
            return render_template(
                'login.html',
                error='Password must contain uppercase, lowercase, number and special character'
            )

        session['user'] = username
        session['email'] = email

        return redirect('/dashboard')

    return render_template('login.html')


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/')

    cursor.execute("""
        SELECT location, sqft, bhk, bath, price
        FROM predictions
        ORDER BY id DESC
        LIMIT 5
    """)

    data = cursor.fetchall()

    formatted_data = []

    total_price = 0

    for row in data:

        price = float(row[4])

        total_price += price

        formatted_price = format_indian_currency(price)

        formatted_data.append((
            row[0],
            row[1],
            row[2],
            row[3],
            formatted_price
        ))

    # Average Price
    avg_price = 0

    if len(data) > 0:

        avg = total_price / len(data)

        avg_price = format_indian_currency(avg)

    return render_template(
        'dashboard.html',
        data=formatted_data,
        avg_price=avg_price
    )


# ---------------- OPEN PREDICT PAGE ----------------
@app.route('/predict-page')
def predict_page():

    if 'user' not in session:
        return redirect('/')

    return render_template(
        'predict.html',
        locations=AREAS,
        prediction_text=""
    )


# ---------------- PREDICT ----------------
@app.route('/predict', methods=['POST'])
def predict():

    if 'user' not in session:
        return redirect('/')

    try:
        location = request.form['location']
        sqft = float(request.form['sqft'])
        bhk = int(request.form['bhk'])
        bath = int(request.form['bath'])

        x = np.zeros(len(columns))

        location_col = "location_" + location

        if location_col in columns:
            x[columns.index(location_col)] = 1

        x[0] = sqft
        x[1] = bhk
        x[2] = bath

        prediction = model.predict([x])[0]

        if prediction < 0:
            prediction = abs(prediction)

        cursor.execute("""
            INSERT INTO predictions
            (location, sqft, bhk, bath, price)
            VALUES (?, ?, ?, ?, ?)
        """, (location, sqft, bhk, bath, float(prediction)))

        conn.commit()

        formatted_price = f"{prediction:,.2f}"

        email = session.get('email')
        username = session.get('user')

        msg = Message(
            subject='House Price Prediction Report',
            sender='predictionsystem17@gmail.com',
            recipients=[email]
        )

        msg.body = f"""
Hello {username},

House Price Prediction Details

Location: {location}
Square Feet: {sqft}
BHK: {bhk}
Bathrooms: {bath}

Predicted Price: ₹{formatted_price}

Thank you for using House AI.
"""
        print("Recipient Email:", email)
        print("Username:", username)
        try:
            mail.send(msg)
            print("Email sent successfully")
        except Exception as mail_error:
            print("MAIL ERROR:", mail_error)

        return render_template(
            'result.html',
            price=formatted_price
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"ERROR: {e}"
# ---------------- INSIGHTS ----------------
@app.route('/insights')
def insights():

    if 'user' not in session:
        return redirect('/')

    cursor.execute("""
        SELECT location, price
        FROM predictions
        ORDER BY id DESC
        LIMIT 5
    """)

    data = cursor.fetchall()

    if len(data) == 0:

        locations = ["No Data"]

        prices = [0]

    else:

        data = data[::-1]

        locations = [row[0] for row in data]

        prices = [row[1] for row in data]

    return render_template(
        'insights.html',
        locations=locations,
        prices=prices
    )


# ---------------- ABOUT ----------------
@app.route('/about')
def about():

    if 'user' not in session:
        return redirect('/')

    return render_template('about.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
