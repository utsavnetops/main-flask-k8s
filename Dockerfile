# Use a lightweight Python image
FROM python:alpine

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . ./

# Expose the application port
EXPOSE 5000

# Run the Flask application
CMD ["python", "app.py"]
