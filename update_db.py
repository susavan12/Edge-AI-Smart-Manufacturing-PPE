import sqlite3

conn = sqlite3.connect("ppe.db")

cursor = conn.cursor()

columns = [
    "employee_id",
    "employee_name",
    "department"
]

for column in columns:

    try:

        cursor.execute(
            f"ALTER TABLE detections ADD COLUMN {column} TEXT"
        )

        print(f"✅ {column} added successfully.")

    except Exception as e:

        print(f"{column} :", e)

conn.commit()
conn.close()

print("Done!")