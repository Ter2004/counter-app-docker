#!/bin/bash

# โหลดค่าตัวแปรจากไฟล์ .env
export $(grep -v '^#' .env | xargs)

# สร้างชื่อ Image เต็มๆ
IMAGE_FULL_NAME=${DOCKER_USER}/${IMAGE_NAME}:${TAG}

echo "Building Image: $IMAGE_FULL_NAME"

# สั่ง Build
docker build -t $IMAGE_FULL_NAME ./backend

# สั่ง Push ขึ้น Cloud
docker push $IMAGE_FULL_NAME

echo "Done! Image pushed to Docker Hub."