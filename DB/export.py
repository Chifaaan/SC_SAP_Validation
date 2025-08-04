import os
import csv
import mysql.connector
from dotenv import load_dotenv


load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_DATABASE'),
}

# Connect to MySQL
conn = mysql.connector.connect(**DB_CONFIG)

cursor = conn.cursor()

# Create export folder if not exists
EXPORT_FOLDER = "exports"
os.makedirs(EXPORT_FOLDER, exist_ok=True)

# Get list of all tables
cursor.execute("SHOW TABLES;")
tables = [table[0] for table in cursor.fetchall()]

# Export each table
for table in tables:
    print(f"📤 Exporting table: {table}")

    cursor.execute(f"SELECT * FROM `{table}`")
    rows = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]

    # Write to CSV
    with open(f"{EXPORT_FOLDER}/{table}.csv", mode="w", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(column_names)
        writer.writerows(rows)

    print(f"✅ {table}.csv saved.")

# Cleanup
cursor.close()
conn.close()