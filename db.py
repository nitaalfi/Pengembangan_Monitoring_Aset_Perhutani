import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # ganti sesuai MySQL kamu
        password="password",  # ganti sesuai MySQL kamu
        database="monitoring_aset"
    )
