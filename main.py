import boto3
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Form
from starlette.responses import Response

router = APIRouter()

# Load AWS credentials from env variables
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_ACCESS_SECRET_KEY")

print(AWS_REGION, S3_BUCKET_NAME, DYNAMODB_TABLE_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

# Initialize S3 and DynamoDB clients
s3_client = boto3.client("s3",
                         region_name=AWS_REGION,
                        aws_access_key_id = AWS_ACCESS_KEY_ID,
                        aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
                         )
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION,  aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

@router.post("/schedule/upload")
async def upload_scheduled_image(file: UploadFile = File(...), scheduled_time: str = Form(...)):
    try:
        # Generate a unique filename
        file_ext = file.filename.split(".")[-1]
        print("ST: ", scheduled_time)
        unique_filename = f"{uuid.uuid4()}.{file_ext}"

        # Upload image to S3
        s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, unique_filename)

        # Get S3 URL
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        image_id = str(uuid.uuid4())

        # Convert scheduled_time to datetime format
        if scheduled_time:
            scheduled_time = datetime.fromisoformat(scheduled_time).isoformat()
            print(scheduled_time)
        else:
            scheduled_time = datetime.utcnow().isoformat()

        # Store metadata in DynamoDB
        table.put_item(Item={
            "Schedule_Partition": image_id,
            "image_url": s3_url,  # S3 image URL
            "scheduled_time": scheduled_time  # When to display the image
        })

        return {"message": "Image scheduled successfully", "image_identifier": image_id, "scheduled_time": scheduled_time}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/{image_id}.jpg")
def get_scheduled_image(image_id: str):
    try:
        # Fetch image metadata from DynamoDB
        response = table.get_item(Key={"Schedule_Partition": image_id})
        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Image not found")

        image_url = response["Item"]["image_url"]

        # Extract S3 object key from the URL
        object_key = image_url.split(f"{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/")[-1]

        # Get image from S3
        s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=object_key)
        image_data = s3_response["Body"].read()

        # Return the image as response
        return Response(content=image_data, media_type="image/jpeg")  # Adjust media_type based on the image type

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))