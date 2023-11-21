FROM python:3.11.5
WORKDIR /Traffic_PubSub/publisher
COPY . /Traffic_PubSub/publisher/
RUN pip install requests
CMD ["python", "./publisher.py"]