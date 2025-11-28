FROM nginx:stable-bullseye
# ลบไฟล์ default เดิมทิ้ง
RUN rm -rf /usr/share/nginx/html/*
# ก๊อปไฟล์ของเราใส่เข้าไป
COPY index.html /usr/share/nginx/html/index.html