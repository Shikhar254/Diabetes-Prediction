from flask import Flask, render_template, request, session, redirect, url_for
import numpy as np
import pickle
import os
from datetime import datetime
import psycopg2
from reportlab.pdfgen import canvas
from flask import send_file
import io




from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# ---------------- SECRET KEY ----------------
app.secret_key = os.getenv("SECRET_KEY", "diabetes_secret_key")

# ---------------- ADMIN LOGIN ----------------
ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")
if not ADMIN_USER or not ADMIN_PASS:
    raise Exception("ADMIN_USER or ADMIN_PASS not set in environment variables!")

# ---------------- DATABASE ----------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("WARNING: DATABASE_URL not found in environment variables")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# ---------------- CREATE TABLE ----------------
def create_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Diabetes Prediction Table
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

        # Pathology Lab Patients Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lab_patients (
                patient_id SERIAL PRIMARY KEY,
                patient_name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                doctor_name TEXT,
                created_at TEXT
            );
        """)

        # Lab Reports Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lab_reports (
                report_id SERIAL PRIMARY KEY,
                patient_id INTEGER REFERENCES lab_patients(patient_id) ON DELETE CASCADE,
                report_date TEXT,
                glucose REAL,
                hba1c REAL,
                blood_pressure TEXT,
                cholesterol REAL,
                hemoglobin REAL,
                remarks TEXT
            );
        """)

        conn.commit()
        cursor.close()
        conn.close()

        print("All tables created successfully!")

    except Exception as e:
        print("DB Error (create_table):", e)

# ---------------- SAVE DATA ----------------
def save_to_database(data):
    try:
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

    except Exception as e:
        print("DB Error (insert):", e)


# Run table creation safely
with app.app_context():
    create_table()


# ---------------- LOAD ML MODEL ----------------
model = pickle.load(open("diabetes_model.pkl", "rb"))
scaler = pickle.load(open("scaler.pkl", "rb"))


# ---------------- ROUTES ----------------
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

    # fix missing values
    if skin == 0:
        skin = 20
    if insulin == 0:
        insulin = 80

    data = np.array([[pregnancies, glucose, bp, skin, insulin, bmi, dpf, age]])
    data = scaler.transform(data)

    prediction = model.predict(data)

    if prediction[0] == 1:
        result = "Diabetes Detected"
        outcome = 1
    else:
        result = "Not Diabetic"
        outcome = 0

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
        result,
        outcome
    ))

    return render_template(
        "result.html",
        prediction=result,
        name=session.get("name"),
        age=session.get("age"),
        gender=session.get("gender"),
        symptoms=session.get("symptoms")
    )
# Pathology home page
@app.route("/lab")
def lab_home():
    return render_template("lab_home.html")

#Patient Registration Page
@app.route("/lab/register", methods=["GET", "POST"])
def lab_register():
    if request.method == "POST":
        patient_name = request.form.get("patient_name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        address = request.form.get("address")
        doctor_name = request.form.get("doctor_name")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO lab_patients (patient_name, age, gender, phone, address, doctor_name, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING patient_id
        """, (patient_name, age, gender, phone, address, doctor_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        patient_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("lab_report_form", patient_id=patient_id))

    return render_template("lab_register.html")

#Report form Page
@app.route("/lab/report/<int:patient_id>", methods=["GET", "POST"])
def lab_report_form(patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM lab_patients WHERE patient_id=%s", (patient_id,))
    patient = cursor.fetchone()

    if request.method == "POST":
        glucose = request.form.get("glucose")
        hba1c = request.form.get("hba1c")
        bp = request.form.get("blood_pressure")
        cholesterol = request.form.get("cholesterol")
        hemoglobin = request.form.get("hemoglobin")

        remarks = "Normal"
        if float(glucose) > 140 or float(hba1c) > 6.5:
            remarks = "High Risk"

        cursor.execute("""
            INSERT INTO lab_reports (patient_id, report_date, glucose, hba1c, blood_pressure, cholesterol, hemoglobin, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING report_id
        """, (
            patient_id,
            datetime.now().strftime("%Y-%m-%d"),
            glucose,
            hba1c,
            bp,
            cholesterol,
            hemoglobin,
            remarks
        ))

        report_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("lab_view_report", report_id=report_id))

    cursor.close()
    conn.close()

    return render_template("lab_report_form.html", patient=patient)

#View Report page
@app.route("/lab/view/<int:report_id>")
def lab_view_report(report_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.report_id, r.report_date, r.glucose, r.hba1c, r.blood_pressure, r.cholesterol, r.hemoglobin, r.remarks,
               p.patient_name, p.age, p.gender, p.phone, p.address, p.doctor_name
        FROM lab_reports r
        JOIN lab_patients p ON r.patient_id = p.patient_id
        WHERE r.report_id = %s
    """, (report_id,))

    report = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("lab_report_view.html", report=report)

#Download Report 
@app.route("/lab/download/<int:report_id>")
def download_report(report_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.report_id, r.report_date, r.glucose, r.hba1c, r.blood_pressure, r.cholesterol, r.hemoglobin, r.remarks,
               p.patient_name, p.age, p.gender, p.phone, p.address, p.doctor_name
        FROM lab_reports r
        JOIN lab_patients p ON r.patient_id = p.patient_id
        WHERE r.report_id = %s
    """, (report_id,))

    report = cursor.fetchone()

    cursor.close()
    conn.close()

    if not report:
        return "Report not found!"

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 800, "Pathology Lab Report")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 760, f"Report ID: {report[0]}")
    pdf.drawString(50, 740, f"Report Date: {report[1]}")

    pdf.drawString(50, 700, f"Patient Name: {report[8]}")
    pdf.drawString(50, 680, f"Age: {report[9]}")
    pdf.drawString(50, 660, f"Gender: {report[10]}")
    pdf.drawString(50, 640, f"Phone: {report[11]}")
    pdf.drawString(50, 620, f"Doctor: {report[13]}")

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, 580, "Test Results:")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 550, f"Glucose: {report[2]} mg/dL")
    pdf.drawString(50, 530, f"HbA1c: {report[3]} %")
    pdf.drawString(50, 510, f"Blood Pressure: {report[4]}")
    pdf.drawString(50, 490, f"Cholesterol: {report[5]} mg/dL")
    pdf.drawString(50, 470, f"Hemoglobin: {report[6]} g/dL")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 430, f"Remarks: {report[7]}")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 100, "Disclaimer: This report is generated digitally for reference purposes.")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"Report_{report_id}.pdf", mimetype="application/pdf")

# ---------------- ADMIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    error = None

    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
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


@app.route("/delete/<int:id>")
def delete_record(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM patient_records WHERE id = %s", (id,))
        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        print("Delete Error:", e)

    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))

@app.route("/lab/dashboard")
def lab_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.report_id, r.report_date, p.patient_name, p.age, p.gender, r.remarks
        FROM lab_reports r
        JOIN lab_patients p ON r.patient_id = p.patient_id
        ORDER BY r.report_id DESC
    """)

    reports = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("lab_dashboard.html", reports=reports)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug= True)