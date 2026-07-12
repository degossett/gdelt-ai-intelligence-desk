# Start with a lightweight Python operating system
FROM python:3.11-slim

# Create a working directory inside the container
WORKDIR /app

# Copy the grocery list and install the packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your Python scripts into the container
COPY . .

# When the container wakes up, run the orchestrator
CMD ["python", "00.0_run_pipeline.py"]
