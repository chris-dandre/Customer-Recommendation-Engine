# Use an official Python runtime as a parent image
FROM python:3.13.2-slim

# Set working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY Agentic_workflow_v7.py .

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI application with optimized Uvicorn settings
CMD ["uvicorn", "Agentic_workflow_v7:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info", "--timeout-keep-alive", "30"]