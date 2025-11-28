FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# คำสั่งแปลงไฟล์ proto เป็น python
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. clicker.proto

CMD ["python", "plugin.py"]