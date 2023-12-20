from flask import Flask, request, jsonify, Blueprint, current_app
from flask_cors import CORS
from werkzeug.utils import secure_filename
from concurrent.futures import ProcessPoolExecutor

from PIL import Image
import boto3
import os
import logging
import cv2

from flask_executor import Executor

imageupload = Blueprint("imageupload", __name__)
executor = Executor()

logging.basicConfig(level=logging.DEBUG)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

progress_data = {}  # Dictionary to store progress data

S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_REGION = os.getenv("S3_REGION")


 

# Specify the correct endpoint based on the error response
S3_ENDPOINT = os.getenv("S3_ENDPOINT")

# Configure S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
    endpoint_url=f"https://{S3_ENDPOINT}",
)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@imageupload.route("/get/files", methods=["POST"])
def upload_aws_file():
    uploaded_files = request.files.getlist("file")
    logging.debug(uploaded_files)

    with ProcessPoolExecutor() as executor:
        futures = []

        for file in uploaded_files:
            if file:
                filename = secure_filename(file.filename)
                media_folder = os.path.join(current_app.root_path, "media", "Test1")
                if not os.path.exists(media_folder):
                    os.makedirs(media_folder, exist_ok=True)
                file_path = os.path.join(media_folder, filename)
                file.save(file_path)

                future = executor.submit(process_uploaded_file, file_path, filename)
                futures.append(future)

                progress_data[filename] = {"loading": 100, "remainingTime": 0}

        # Wait for all futures to complete
        for future in futures:
            future.result()

    return jsonify({"message": "Files uploaded successfully"})


 


def process_uploaded_file(file_path, filename):
    if file_path.endswith((".mp4", ".avi")):
        process_video(file_path)

    upload_to_s3(file_path, filename)


def process_video(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return

    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))

    out = cv2.VideoWriter(
        "processed_video.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 20.0, (300, 300)
    )

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        resized_frame = cv2.resize(frame, (300, 300))

        out.write(resized_frame)

    cap.release()
    out.release()

    print("Video processing complete.")


def upload_to_s3(file_path, filename):
    s3_folder_full = "photos/full"
    s3_folder_resized = "photos/resized"
    s3_folder_thumbnails = "photos/thumbnails"

    s3_key_full = f"{s3_folder_full}/{filename}"

    with open(file_path, "rb") as data:
        s3.upload_fileobj(data, S3_BUCKET, s3_key_full)

    resized_file_path = resize_image(file_path, max_size=(1000, 1000))
    s3_key_resized = f"{s3_folder_resized}/{filename}"

    with open(resized_file_path, "rb") as resized_data:
        s3.upload_fileobj(resized_data, S3_BUCKET, s3_key_resized)

    thumbnail_file_path = resize_image(file_path, max_size=(400, 400))
    s3_key_thumbnail = f"{s3_folder_thumbnails}/{filename}"

    with open(thumbnail_file_path, "rb") as thumbnail_data:
        s3.upload_fileobj(thumbnail_data, S3_BUCKET, s3_key_thumbnail)

    os.remove(file_path)
    os.remove(resized_file_path)
    os.remove(thumbnail_file_path)

    print(f"Files {filename} uploaded to S3 and removed locally.")


def resize_image(file_path, max_size=(1200, 1200)):
    original_image = cv2.imread(file_path)

    original_height, original_width, _ = original_image.shape
    aspect_ratio = original_width / original_height

    if aspect_ratio > 1:
        new_width = min(original_width, max_size[0])
        new_height = round(new_width / aspect_ratio)
    else:
        new_height = min(original_height, max_size[1])
        new_width = round(new_height * aspect_ratio)

    resized_image = cv2.resize(
        original_image, (new_width, new_height), interpolation=cv2.INTER_AREA
    )

    resized_filename = file_path.replace(".", f"_resized_{max_size[0]}x{max_size[1]}.")

    cv2.imwrite(resized_filename, resized_image)

    return resized_filename

 


@imageupload.route("/get/progress/<filename>", methods=["GET"])
def get_upload_progress(filename):
    progress = progress_data.get(filename, {"loading": 0, "remainingTime": 0})
    return jsonify(progress)
