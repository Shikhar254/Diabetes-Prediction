import sqlite3

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