# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container
WORKDIR /Traffic_PubSub

# Copy the current directory contents into the container at /app
COPY app.py .

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade flask
RUN pip install --upgrade werkzeug

# Make port 5000 available to the world outside this container
EXPOSE 5002 8888 8889 8890

# Define environment variable
#ENV NAME World

# Run app.py when the container launches
CMD ["python", "app.py"]
