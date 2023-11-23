FROM python:3.11.5

WORKDIR /Traffic_PubSub/publisher

# Copy the entire project into the container
COPY . .

RUN pip install requests
#RUN pip install -r requirements.txt
CMD [ "python3","publisher.py" ]

