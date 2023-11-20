FROM python:3.11.5
WORKDIR /Traffic_PubSub/broker
COPY broker.py /Traffic_PubSub/broker/
# Expose a port (you can expose a default one here, it can be overridden at runtime)
EXPOSE 8888
# Command to run the broker script
CMD ["python", "./broker.py"]

#FROM python:3.11.5

#WORKDIR /Traffic_PubSub/broker

# Copy the entire project into the container
#COPY . .

# Ensure the script is executable
#RUN chmod +x start_script.sh

#RUN apt-get update && apt-get install -y telnet
# Install net-tools package for netstat
#RUN apt-get install -y net-tools

# Install iproute2 package for ss
#RUN apt-get install -y iproute2

#EXPOSE 5060 5061 5062
# Run start_script.sh when the container launches
#CMD ["./start_script.sh"]