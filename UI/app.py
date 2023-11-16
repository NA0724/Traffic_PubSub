
from flask import Flask, render_template, request, jsonify
import json
import socket
import threading
from publisher import publisher
from subscriber import subscriber
from broker import TrafficBroker

app = Flask(__name__)

# Endpoint to render the main index page
@app.route("/")
def index():
    return render_template("index.html")

# Endpoint to render the publisher page
@app.route("/publisher")
def show_publisher():
    return render_template("publisher.html")

# Endpoint to handle publishing messages
@app.route("/publish", methods=["POST"])
def publish_message():
    data = request.json
    topic = data["topic"]
    message = data["message"]
    # Call the publisher function with the provided topic and message
    # This part can be adjusted based on how the 'publisher' function is implemented in 'publisher.py'
    threading.Thread(target=publisher, args=(topic, message)).start()
    return jsonify({"status": "Message published"})

# Endpoint to render the subscriber page
@app.route("/subscriber")
def show_subscriber():
    return render_template("subscriber.html")

# Endpoint to handle subscription requests
@app.route("/subscribe", methods=["POST"])
def subscribe_to_topic():
    data = request.json
    topic = data["topic"]
    # Call the subscriber function with the provided topic
    # This part can be adjusted based on how the 'subscriber' function is implemented in 'subscriber.py'
    threading.Thread(target=subscriber, args=(topic,)).start()
    return jsonify({"status": "Subscribed to topic"})

# Endpoint to render the broker status page
@app.route("/broker_status")
def broker_status():
    return render_template("broker_status.html")

# Function to start the broker in a separate thread
def start_broker():
    broker = TrafficBroker()
    broker.run()

if __name__ == "__main__":
    # Start the broker thread
    threading.Thread(target=start_broker, daemon=True).start()
    # Run the Flask app
    app.run(debug=True)
