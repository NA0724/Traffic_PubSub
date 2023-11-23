FROM python:3.11.5

WORKDIR /Traffic_PubSub/subscriber

# Copy the entire project into the container
COPY . .

RUN pip install requests
# Run the subscriber.py script when the container launches
CMD [ "python3","subscriber.py"]

