# Traffic_PubSub

### Build Docker Image for Broker, Subscriber and Publisher from respective dockerfiles
`docker build -t broker_image .`
`docker build -t subscriber_image .`
`docker build -t publisher_image .`

### create network for containers
`docker network create --driver bridge traffic_network`

### Run broker containers in the same network
`docker run -d --name broker1 --network traffic_network -p 8888:8888 broker_image python ./broker.py --host broker1 --port 8888 --cluster broker2:8889 broker3:8890`
`docker run -d --name broker2 --network traffic_network -p 8889:8889 broker_image python ./broker.py --host broker2 --port 8889 --cluster broker1:8888 broker3:8890`
`docker run -d --name broker3 --network traffic_network -p 8890:8890 broker_image python ./broker.py --host broker3 --port 8890 --cluster broker1:8888 broker2:8889`

### Run subscriber container
`docker run -d --name subscriber1 --network traffic_network subscriber_image python3 ./subscriber.py "sub1" "broker1:8888" "broker2:8889" "broker3:8890" "Santa Clara"`
`docker run -d --name subscriber2 --network traffic_network subscriber_image python3 ./subscriber.py "sub2" "broker1:8888" "broker2:8889" "broker3:8890" "Santa Clara" "Alameda"`
`docker run -d --name subscriber3 --network traffic_network subscriber_image python3 ./subscriber.py "sub3" "broker1:8888" "broker2:8889" "broker3:8890" "Santa Cruz" "San Francisco"`

### Run publisher container
`docker run -d --name publisher --network traffic_network publisher_image python3 ./publisher.py "broker1:8888" "broker2:8889" "broker3:8890"`


### Run Flask container
`docker run -d --name flask --network traffic_network trafficpubsub python3 ./app.py`