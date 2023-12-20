import os, boto3
from flask import Flask, request, jsonify, current_app, Blueprint
from werkzeug.utils import secure_filename
from deepface import DeepFace
import datetime, requests
from werkzeug.utils import secure_filename
from io import BytesIO
import numpy as np
from PIL import Image
import datetime, cv2
from botocore.exceptions import NoCredentialsError

faceapp = Blueprint("faceapp", __name__)


S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_REGION = os.getenv("S3_REGION")

UPLOAD_FOLDER = "Test"
S3_ENDPOINT = os.getenv("S3_ENDPOINT")

 

# Configure S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
)


def get_s3_images():
    objects = s3.list_objects(Bucket=S3_BUCKET)
    image_urls = [
        f"https://{S3_ENDPOINT}/{obj['Key']}"
        for obj in objects.get("Contents", [])
        if "photos/resized" in obj["Key"]
    ]

    print(image_urls)
    return image_urls


@faceapp.route("/api/face_recognition", methods=["POST"])
def face_recognition_api():
    print("Request Headers:", request.headers)
    print("Request Form Data:", request.form)

    uploaded_files = request.files.getlist("file")
    print("Uploaded Files:", uploaded_files)

    matched_faces = []

    s3_images = get_s3_images()

    for file in uploaded_files:
        if file:
            filename = secure_filename(file.filename)
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{timestamp}_{filename}"
            file.save(unique_filename)

            try:
                img1_bgr = cv2.imread(unique_filename)

                verified_photos = []
                for s3_image_url in s3_images:
                    # Download image from URL
                    response = requests.get(s3_image_url)
                    img2_array = np.frombuffer(response.content, np.uint8)
                    img2_bgr = cv2.imdecode(img2_array, cv2.IMREAD_COLOR)

                    # Verify faces
                    result = DeepFace.verify(img1_bgr, img2_bgr, model_name="Facenet")
                    print(result)

                    # Check if verification is true
                    if (
                        result["verified"] and result["distance"] < 0.6
                    ):  # Adjust the threshold as needed
                        result["verified"] = str(result["verified"])
                        result["photo_url"] = s3_image_url
                        verified_photos.append(result)

                if verified_photos:
                    # If at least one photo is verified, append it to the matched_faces list
                    matched_faces.extend(verified_photos)
                else:
                    # If no photos are verified, add a placeholder entry with the current file
                    matched_faces.append(
                        {
                            "verified": False,
                            "photo_url": f"Local file: {unique_filename}",
                        }
                    )

            except Exception as e:
                print(f"Error processing file {unique_filename}: {str(e)}")

    # Return the matched faces as JSON response
    return jsonify(matched_faces)

 
