from flask import Flask, render_template, request, session, redirect, url_for
import numpy as np
import pickle
import os
from datetime import datetime
import psycopg2

app = Flask(__name__)

# ---------------------- SECRET KEY ----------------------
app.secret_key = os.getenv("SECRET_KEY", "diabetes_secret_key")

# ---------------------- ADMIN LOGIN VARIABLES ----------------------
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

# ---------------------- DATABASE URL (Railway PostgreSQL) ----------------------
DATABASE_URL = os.getenv("DATABASE_URL")


# ---------------------- DATABASE CONNECTION ----------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# ---------------------- CREATE TABLE ----------------------
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_records (
            id SERIAL PRIMARY KEY,
            datetime TEXT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            symptoms TEXT,
            pregnancies REAL,
            glucose REAL,
            bloodpressure REAL,
            skinthickness REAL,
            insulin REAL,
            bmi REAL,
            dpf REAL,
            prediction TEXT,
            outcome INTEGER
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ---------------------- SAVE DATA ----------------------
def save_to_database(data):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO patient_records (
            datetime, name, age, gender, symptoms,
            pregnancies, glucose, bloodpressure, skinthickness, insulin,
            bmi, dpf, prediction, outcome
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, data)

    conn.commit()
    cursor.close()
    conn.close()


# Create table when app starts
create_table()


# ---------------------- LOAD MODEL + SCALER ----------------------
model = pickle.load(open("diabetes_model.pkl", "rb"))
scaler = pickle.load(open("scaler.pkl", "rb"))


# ---------------------- ROUTES ----------------------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/patient")
def patient():
    return render_template("patient.html")


@app.route("/form", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        session["name"] = request.form.get("name")
        session["age"] = request.form.get("age")
        session["gender"] = request.form.get("gender")

        symptoms = request.form.getlist("symptoms")
        session["symptoms"] = ", ".join(symptoms)

    return render_template(
        "form.html",
        name=session.get("name"),
        age=session.get("age"),
        gender=session.get("gender"),
        symptoms=session.get("symptoms")
    )


@app.route("/predict", methods=["POST"])
def predict():
    pregnancies = float(request.form.get("Pregnancies", 0))
    glucose = float(request.form.get("Glucose", 0))
    bp = float(request.form.get("BloodPressure", 0))
    skin = float(request.form.get("SkinThickness", 0))
    insulin = float(request.form.get("Insulin", 0))
    bmi = float(request.form.get("BMI", 0))
    dpf = float(request.form.get("DiabetesPedigreeFunction", 0))
    age = float(request.form.get("Age", session.get("age", 0)))

    # Fix missing values
    if skin == 0:
        skin = 20
    if insulin == 0:
        insulin = 80

    # Prepare input
    data = [pregnancies, glucose, bp, skin, insulin, bmi, dpf, age]
    final_data = np.array([data])

    # Scale input data
    final_data = scaler.transform(final_data)

    # Prediction
    prediction = model.predict(final_data)

    if prediction[0] == 1:
        prediction_result = "Diabetes Detected"
        outcome = 1
    else:
        prediction_result = "Not Diabetic"
        outcome = 0

    # Save record into PostgreSQL
    save_to_database((
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        session.get("name"),
        int(age),
        session.get("gender"),
        session.get("symptoms"),
        pregnancies,
        glucose,
        bp,
        skin,
        insulin,
        bmi,
        dpf,
        prediction_result,
        outcome
    ))

    return render_template(
        "result.html",
        prediction=prediction_result,
        name=session.get("name"),
        age=session.get("age"),
        gender=session.get("gender"),
        symptoms=session.get("symptoms")
    )


# ---------------------- ADMIN LOGIN ----------------------

@app.route("/admin", methods=["GET", "POST"])
def admin():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid Username or Password!"

    return render_template("admin.html", error=error)


@app.route("/dashboard")
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patient_records ORDER BY id DESC")
    records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("dashboard.html", records=records)


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))


# ---------------------- RUN APP ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)