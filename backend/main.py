from fastapi import FastAPI, HTTPException
import mysql.connector
import os
import time
import grpc
import clicker_pb2
import clicker_pb2_grpc
import pika
import json
from datetime import datetime, timedelta  # ✅ เพิ่ม timedelta

app = FastAPI()

# --- Configuration ---
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "secret")
DB_NAME = os.getenv("DB_NAME", "counter_db")

PLUGIN_HOST = os.getenv("PLUGIN_HOST", "plugin")
PLUGIN_PORT = os.getenv("PLUGIN_PORT", "50051")
RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")

# --- Database Helpers ---
def get_db_connection():
    try:
        return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    except:
        return None

def init_db():
    """สร้างตารางตอนเริ่มต้น"""
    time.sleep(5) 
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
        print("Database Initialized")
    except Exception as e:
        print(f"Init DB Error: {e}")

init_db()

# --- RabbitMQ Helper ---
def publish_event(event_type, current_value):
    try:
        credentials = pika.PlainCredentials('user', 'password')
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST, credentials=credentials))
        channel = connection.channel()
        channel.queue_declare(queue='history_queue')
        
        # ✅ แก้เวลาเป็น UTC+7 (เวลาไทย)
        thai_time = (datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        
        message = {
            "timestamp": thai_time,
            "event_type": event_type,
            "value": current_value
        }
        
        channel.basic_publish(exchange='', routing_key='history_queue', body=json.dumps(message))
        connection.close()
        print(f"Sent event to RabbitMQ: {message}")
    except Exception as e:
        print(f"Failed to publish to RabbitMQ: {e}")

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Microservices Clicker API"}

@app.get("/count")
def get_count():
    conn = get_db_connection()
    if not conn: return {"value": 0}
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT value FROM counters WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {"value": result['value']}
    else:
        return {"value": 0}

@app.post("/count")
def increment_count():
    conn = get_db_connection()
    if not conn: 
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    # 1. ดึงค่าเก่า
    cursor.execute("SELECT value FROM counters WHERE id = 1")
    res = cursor.fetchone()
    current_val = res['value'] if res else 0
    
    # 2. ส่งไปคำนวณที่ Plugin (gRPC)
    try:
        channel = grpc.insecure_channel(f'{PLUGIN_HOST}:{PLUGIN_PORT}')
        stub = clicker_pb2_grpc.ClickerServiceStub(channel)
        response = stub.Calculate(clicker_pb2.ClickRequest(current_value=current_val))
        new_val = response.new_value
    except Exception as e:
        print(f"Plugin Error: {e}")
        conn.close()
        raise HTTPException(status_code=500, detail=f"Plugin Error: {e}")

    # 3. อัปเดตค่าใหม่ลง DB
    cursor.execute("UPDATE counters SET value = %s WHERE id = 1", (new_val,))
    conn.commit()
    
    # 4. ส่งจดหมายหา RabbitMQ (History Service)
    publish_event("Increase", new_val)
    
    # 5. ดึงค่าล่าสุดมาส่งกลับ
    cursor.execute("SELECT value FROM counters WHERE id = 1")
    final_result = cursor.fetchone()
    conn.close()
    
    return {"value": final_result['value']}