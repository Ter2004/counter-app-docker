# ใช้ Python Image พื้นฐาน
FROM python:3.9-slim

# ตั้ง Folder ทำงาน
WORKDIR /app

# Copy ไฟล์ dependencies ไปลงก่อน (เพื่อความเร็วในการ Build ครั้งถัดไป)
COPY requirements.txt .

# ติดตั้ง Library
RUN pip install --no-cache-dir -r requirements.txt

# Copy โค้ดทั้งหมด
COPY . .

RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. clicker.proto
# รัน Server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]