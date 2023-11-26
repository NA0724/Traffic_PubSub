document.addEventListener('DOMContentLoaded', function() {
    // Handle form submission for publishing messages
    const publishForm = document.querySelector('#publish-form');
    publishForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const message = document.querySelector('#publish-message').value;
        fetch('/publish', {
            method: 'POST',
            body: JSON.stringify({ message: message }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the UI to show the published message
                const messagesDiv = document.querySelector('#published-messages');
                messagesDiv.innerHTML += `<p>${data.message}</p>`;
            }
        });
    });

    // Handle form submission for subscribing to topics
    const subscribeForm = document.querySelector('#subscribe-form');
    subscribeForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const topic = document.querySelector('#subscribe-topic').value;
        fetch('/subscribe', {
            method: 'POST',
            body: JSON.stringify({ topic: topic }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the UI to show the subscribed topic
                const topicsDiv = document.querySelector('#subscribed-topics');
                topicsDiv.innerHTML += `<p>${data.topic}</p>`;
            }
        });
    });

    // Periodically check and update broker status
    setInterval(() => {
        fetch('/broker_status')
        .then(response => response.json())
        .then(data => {
            const brokerStatusDiv = document.querySelector('#broker-status');
            brokerStatusDiv.innerHTML = `Broker Status: ${data.status}`;
        });
    }, 5000); // Update every 5 seconds
});
