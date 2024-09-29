# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY bot.py ./

# The bot token can be provided via environment variables
# It's better not to hardcode it in the Dockerfile

# Command to run the bot
CMD ["python", "bot.py"]
