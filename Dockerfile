# Use official Python image
FROM python:3.11

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app files
COPY . .

# Expose the FastAPI default port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "main:router", "--host", "0.0.0.0", "--port", "8000"]