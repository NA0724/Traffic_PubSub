FROM python:3.11.5
WORKDIR /Traffic_PubSub/broker
COPY broker.py /Traffic_PubSub/broker/
# Expose a port (you can expose a default one here, it can be overridden at runtime)
EXPOSE 8888
# Command to run the broker script
CMD ["python", "./broker.py"]


