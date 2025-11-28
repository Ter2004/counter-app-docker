from fastapi import FastAPI
import uvicorn
import mysql.connector
import pika
import json
import os
import threading
import time

app = FastAPI()

# Config
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = "root"
DB_PASS = "secret"
DB_NAME = "counter_db"
RABBIT_HOST = "rabbitmq"

def init_history_table():
    """สร้างตาราง History"""
    time.sleep(10) # รอ DB บูท
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp VARCHAR(50),
                event_type VARCHAR(50),
                value INT
            )
        """)
        conn.commit()
        conn.close()
        print("History Table Created")
    except Exception as e:
        print(f"Init DB Error: {e}")

def consume_messages():
    """ฟังก์ชันเฝ้ารอรับจดหมาย (รันตลอดเวลา)"""
    time.sleep(15) # รอ RabbitMQ บูท
    try:
        credentials = pika.PlainCredentials('user', 'password')
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST, credentials=credentials))
        channel = connection.channel()
        channel.queue_declare(queue='history_queue')

        def callback(ch, method, properties, body):
            data = json.loads(body)
            print(f"Received: {data}")
            # บันทึกลง DB
            try:
                conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO history (timestamp, event_type, value) VALUES (%s, %s, %s)", 
                               (data['timestamp'], data['event_type'], data['value']))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Save Error: {e}")

        channel.basic_consume(queue='history_queue', on_message_callback=callback, auto_ack=True)
        print("Waiting for messages...")
        channel.start_consuming()
    except Exception as e:
        print(f"RabbitMQ Error: {e}")

# เริ่มทำงานตอนเปิด App
@app.on_event("startup")
def startup_event():
    threading.Thread(target=init_history_table).start()
    threading.Thread(target=consume_messages, daemon=True).start()

@app.get("/history")
def get_history():
    """API สำหรับให้ Frontend ดึงประวัติ"""
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT 10")
        result = cursor.fetchall()
        conn.close()
        return result
    except:
        return []

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)