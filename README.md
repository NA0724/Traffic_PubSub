# Traffic_PubSub




 ## Setup the application: Steps
 - Install python (We have used python:3.11)
 - Install Docker for desktop. (We have used Docker [Docker version 20.10.24, build 297e128] for Mac.)
 - Install Docker extension in Visual Studio Code Editor
 - The project structure looks like this:

```
Traffic_pubsub/
│
├── broker/
│   ├── __init__.py
│   ├── broker.py
│   └── Dockerfile
│
├── subscriber/
│   ├── __init__.py
│   ├── subscriber.py
│   └── Dockerfile
│
├── flask/
│   ├── __init__.py
│   ├── app.py
│   ├── Dockerfile
│   ├── templates/
│   │   ├── index.html
│   │   └── error.html
│   │   └── subscriber_data.html
│   │   └── success.html
│   └── static/
│       ├── css/
│       │   ├── style.css
│       │   └── ...
│       └── images/
│           ├── traffic.jpg
│           └── ...
│
├── publisher/
│   ├── __init__.py
│   ├── publisher.py
│   ├── traffic_data_fetcher.py
│   └── Dockerfile
│
└── README.md
└── docker-compose.yml
└── docker-compose.debug.yml
```

- Once the environment setup is done, create the images from the Dockerfiles for subscriber, publisher and broker. Open the terminal and run the following commands. 

#### Build Docker Image for Broker, Subscriber and Publisher from respective dockerfiles
`docker build -t broker_image broker`
`docker build -t subscriber_image subscriber`
`docker build -t publisher-image publisher`
`docker build -t trafficpubsub_image flask`

#### Create network for containers
`docker network create --driver bridge traffic_network`

#### Run 3 broker containers in the same network 
`docker run -d --name broker1 --network traffic_network -p 8888:8888 broker_image python ./broker.py --host broker1 --port 8888 --cluster broker2:8889 broker3:8890`
`docker run -d --name broker2 --network traffic_network -p 8889:8889 broker_image python ./broker.py --host broker2 --port 8889 --cluster broker1:8888 broker3:8890`
`docker run -d --name broker3 --network traffic_network -p 8890:8890 broker_image python ./broker.py --host broker3 --port 8890 --cluster broker1:8888 broker2:8889`

- Once the cluster of brokers is created, in the docker application, we can verify that the leader broker is also elected. And all other brokers are connected to each other and gossipping about the status and subscriptions of each other.
- Now Run the container to start the application.

#### Run Flask container
`docker run -v /var/run/docker.sock:/var/run/docker.sock -d --name trafficpubsub --network traffic_network -p 5002:5002 trafficpubsub_image python3 ./app.py`




## Steps to manually run subscriber and publsiher. 
(Not needed if flask is running.)
#### Run subscriber container
`docker run -d --name subscriber1 --network traffic_network subscriber_image python3 ./subscriber.py "sub1" "broker1:8888" "broker2:8889" "broker3:8890" "Santa Clara"`

#### Run publisher container
`docker run -d --name publisher --network traffic_network publisher_image python3 ./publisher.py "broker1:8888" "broker2:8889" "broker3:8890"`




