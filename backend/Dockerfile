# Use a lightweight official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your python scripts into the container
COPY . .

# Expose the API port (8000 TCP) and the UDP port (5000 UDP)
EXPOSE 8000
EXPOSE 5000/udp

# The command to start the server, binding to 0.0.0.0 so it can be reached externally
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]