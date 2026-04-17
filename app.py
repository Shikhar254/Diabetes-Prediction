from flask import Flask, render_template, request, session, redirect, url_for
import numpy as np
import pickle
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# SECRET KEY from Render Environment Variables
app.secret_key = os.getenv("SECRET_KEY", "diabetes_secret_key")

# ADMIN LOGIN from Render Environment Variables
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")


# ---------------------- DATABASE SETUP ----------------------
def create_table():
    conn = sqlite3.connect("patients.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    )
    """)

    conn.commit()
    conn.close()


def save_to_database(data):
    conn = sqlite3.connect("patients.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO patient_records (
        datetime, name, age, gender, symptoms,
        pregnancies, glucose, bloodpressure, skinthickness, insulin,
        bmi, dpf, prediction, outcome
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    conn.close()


# Create table if not exists
create_table()


# ---------------------- LOAD MODEL ----------------------
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

    # Input Data
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

    # Save to Database
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

    conn = sqlite3.connect("patients.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patient_records ORDER BY id DESC")
    records = cursor.fetchall()

    conn.close()

    return render_template("dashboard.html", records=records)


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True)