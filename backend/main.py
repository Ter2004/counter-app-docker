from fastapi import FastAPI, HTTPException
import mysql.connector
import os
import time
import grpc
import clicker_pb2
import clicker_pb2_grpc

app = FastAPI()

# Config Database
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "secret")
DB_NAME = os.getenv("DB_NAME", "counter_db")

# Config Plugin (Microkernel)
PLUGIN_HOST = os.getenv("PLUGIN_HOST", "plugin")
PLUGIN_PORT = os.getenv("PLUGIN_PORT", "50051")

def get_db_connection():
    retries = 5
    while retries > 0:
        try:
            return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
        except:
            time.sleep(2)
            retries -= 1
    return None

def init_db():
    # สร้าง Database และ Table ถ้ายังไม่มี (เผื่อรันครั้งแรก)
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.close()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS counters (id INT PRIMARY KEY, value INT)")
        cursor.execute("INSERT IGNORE INTO counters (id, value) VALUES (1, 0)")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Init DB Error: {e}")

# รันสร้างตารางตอนเปิดแอป
init_db()

@app.get("/")
def read_root():
    return {"message": "Microkernel Clicker API"}

# ✅ ฟังก์ชันนี้คือส่วนที่ขาดไป (ทำให้ขึ้น undefined)
@app.get("/count")
def get_count():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT value FROM counters WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    
    # ถ้าไม่มีข้อมูล ให้คืนค่า 0
    if not result:
        return {"value": 0}
        
    return result

@app.post("/count")
def increment_count():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    # 1. ดึงค่าปัจจุบันจาก DB
    cursor.execute("SELECT value FROM counters WHERE id = 1")
    result = cursor.fetchone()
    current_val = result['value'] if result else 0
    
    # 2. ส่งไปให้ Plugin คำนวณ (เรียกผ่าน gRPC)
    try:
        channel = grpc.insecure_channel(f'{PLUGIN_HOST}:{PLUGIN_PORT}')
        stub = clicker_pb2_grpc.ClickerServiceStub(channel)
        
        # ส่ง Request
        response = stub.Calculate(clicker_pb2.ClickRequest(current_value=current_val))
        new_val = response.new_value
        
    except Exception as e:
        print(f"Plugin Error: {e}")
        conn.close()
        # Fallback: ถ้า Plugin พัง ให้บวก 1 แบบเดิม (หรือจะ error เลยก็ได้)
        raise HTTPException(status_code=500, detail=f"Plugin Error: {e}")

    # 3. อัปเดตค่าใหม่ลง DB
    cursor.execute("UPDATE counters SET value = %s WHERE id = 1", (new_val,))
    conn.commit()
    
    # 4. ส่งผลลัพธ์กลับ
    cursor.execute("SELECT value FROM counters WHERE id = 1")
    final_result = cursor.fetchone()
    conn.close()
    return final_result