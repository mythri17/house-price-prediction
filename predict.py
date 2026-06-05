from flask import Flask, render_template, request
import pickle
import pandas as pd

app = Flask(__name__)

# -------------------- LOAD MODEL --------------------
model = pickle.load(open('model.pkl', 'rb'))
model_columns = pickle.load(open('columns.pkl', 'rb'))

# -------------------- LOCATIONS --------------------
BENGALURU_AREAS = sorted([
    col.replace('location_', '')
    for col in model_columns
    if col.startswith('location_')
])

# -------------------- FORMAT INDIAN CURRENCY --------------------
def format_indian_currency(num):

    num = int(num)
    s = str(num)

    last3 = s[-3:]
    rest = s[:-3]

    if rest != '':
        rest = rest[::-1]

        parts = [
            rest[i:i + 2]
            for i in range(0, len(rest), 2)
        ]

        rest = ','.join(parts)[::-1]

        return rest + ',' + last3

    else:
        return last3


# -------------------- VALIDATION --------------------
def check_range(sqft, bhk, bath):

    if sqft < 1000 or sqft > 5000:
        return "❌ Sqft must be between 1000 - 5000"

    if bhk < 1 or bhk > 8:
        return "❌ BHK must be between 1 - 8"

    if bath < 1 or bath > 6:
        return "❌ Bathrooms must be between 1 - 6"

    return "OK"


# -------------------- HOME PAGE --------------------
@app.route('/')
def home():

    return render_template(
        'predict.html',
        prediction_text="",
        locations=BENGALURU_AREAS
    )


# -------------------- PREDICT --------------------
@app.route('/predict', methods=['POST'])
def predict():

    try:

        # -------- GET INPUTS --------
        location = request.form['location'].strip()

        sqft = float(request.form['sqft'])

        bhk = int(request.form['bhk'])

        bath = int(request.form['bath'])

        # -------- LOCATION CHECK --------
        if location not in BENGALURU_AREAS:

            return render_template(
                'predict.html',
                prediction_text="❌ Invalid Location",
                locations=BENGALURU_AREAS
            )

        # -------- VALIDATION --------
        validation = check_range(sqft, bhk, bath)

        if validation != "OK":

            return render_template(
                'predict.html',
                prediction_text=validation,
                locations=BENGALURU_AREAS
            )

        # -------- CREATE INPUT --------
        input_dict = {}

        for col in model_columns:
            input_dict[col] = 0

        # Numerical Values
        input_dict['total_sqft'] = sqft
        input_dict['bhk'] = bhk
        input_dict['bath'] = bath

        # Location
        location_column = 'location_' + location

        if location_column in input_dict:
            input_dict[location_column] = 1

        # -------- DATAFRAME --------
        df_input = pd.DataFrame([input_dict])

        df_input = df_input[model_columns]

        # -------- PREDICT --------
        prediction = model.predict(df_input)[0]

        # Avoid negative values
        if prediction < 0:
            prediction = abs(prediction)

        # -------- FORMAT PRICE --------
        formatted_price = format_indian_currency(prediction)

        # -------- RETURN RESULT --------
        return render_template(
            'predict.html',
            prediction_text=f"🏠 Estimated Price: ₹ {formatted_price}",
            locations=BENGALURU_AREAS
        )

    except Exception as e:

        return render_template(
            'predict.html',
            prediction_text=f"❌ Error: {str(e)}",
            locations=BENGALURU_AREAS
        )


# -------------------- RUN APP --------------------
if __name__ == "__main__":

    print("🚀 Server Starting...")

    app.run(debug=True)