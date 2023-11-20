FROM python:3.11.5

WORKDIR /Traffic_PubSub/publisher

# Copy the entire project into the container
COPY . .

RUN pip install requests
EXPOSE 8888

CMD [ "python3","publisher.py" ]