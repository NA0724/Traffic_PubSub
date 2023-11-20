from flask import Flask, render_template
import threading
import time
from broker.broker import TrafficBroker, parse_args

app = Flask(__name__)

# Global variable to hold the broker instance
broker = None

@app.route('/')
def homepage():
    return render_template('index.html', leader_address=get_leader_address())

def get_leader_address():
    if broker:
        return broker.get_leader_address()
    return "Broker not initialized"

def run_broker():
    global broker
    args = parse_args()

    # Convert cluster addresses from string "host:port" to tuple (host, port)
    cluster_addresses = []
    for addr in args.cluster:
        host, port = addr.split(":")
        cluster_addresses.append((host, int(port)))

    broker = TrafficBroker(args.host, args.port, cluster_addresses)
    # Run the broker server loop in a separate thread
    broker_thread = threading.Thread(target=broker.run)
    broker_thread.start()

    # Optionally, add a small delay to ensure the server is fully up
    time.sleep(1)

    # Start Flask app
    app.run(port=5002, debug=True)

if __name__ == "__main__":
    # Run the broker and Flask app
    run_broker()
