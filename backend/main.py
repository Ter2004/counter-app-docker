from fastapi import FastAPI, HTTPException
import mysql.connector
import os
import time

app = FastAPI()

# อ่านค่า Config จาก Environment Variable (ที่ตั้งใน docker-compose)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "secret")
DB_NAME = os.getenv("DB_NAME", "counter_db")

def get_db_connection():
    """ฟังก์ชันเชื่อมต่อ Database พร้อมระบบ Retry"""
    retries = 5
    while retries > 0:
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            return conn
        except mysql.connector.Error:
            # ถ้าต่อไม่ได้ (เช่น DB กำลังบูท) ให้รอ 5 วินาทีแล้วลองใหม่
            print("Database not ready, retrying in 5 seconds...")
            time.sleep(5)
            retries -= 1
            
    # ถ้ายังไม่ได้อีก ให้ลองเชื่อมต่อแบบไม่มีชื่อ DB เพื่อสร้าง DB ก่อน
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.close()
        # ลองต่อใหม่อีกครั้ง
        return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    except Exception as e:
        print(f"Final connection failed: {e}")
        return None

def init_db():
    """สร้างตารางถ้ายังไม่มี"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counters (
                id INT PRIMARY KEY,
                value INT
            )
        """)
        # ใส่ค่าเริ่มต้นเป็น 0 ถ้ายังไม่มีข้อมูล
        cursor.execute("INSERT IGNORE INTO counters (id, value) VALUES (1, 0)")
        conn.commit()
        conn.close()
        print("Database initialized.")

# รันคำสั่งสร้างตารางตอนเปิดแอป
init_db()

@app.get("/")
def read_root():
    return {"message": "Counter API is running"}

@app.get("/count")
def get_count():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT value FROM counters WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    return result

@app.post("/count")
def increment_count():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    cursor = conn.cursor(dictionary=True)
    # เพิ่มค่าทีละ 1
    cursor.execute("UPDATE counters SET value = value + 1 WHERE id = 1")
    conn.commit()
    
    # ดึงค่าล่าสุดมาแสดง
    cursor.execute("SELECT value FROM counters WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    return result