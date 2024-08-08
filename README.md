# LineReminderAssistant: A ChatBot for Tasks Reminder

This project is a Linebot application that leverages Natural Language Processing (NLP) to provide reminder service through chat based on users' requests. The bot is designed to understand and process natural language queries, offering a more humanized reminder for users on the LINE messaging platform.

## Features

- **Natural Language Understanding**: The bot can comprehend and respond to a variety of user time-reminding requests using advanced NLP techniques.
- **Real-Time Reminder**: Built to handle real-time tasks reminder from all users through Google Cloud Scheduler.
- **Scalable and Reliable**: Built to handle multiple users simultaneously with robust error handling and performance optimization by utilizing kubernetes.

## Getting Started

To get started with the LineReminderAssistant, follow the instructions below to set up and run the application.

### Prerequisites

- Python 3.9
- LINE Developer Account
- Required Python libraries (listed in `requirements.txt`)
- GCP (Google Cloud Platform)

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/elanehan/linebot-reminder.git
    cd linebot-reminder
    ```

2. Switch to directories of each service and install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Set up your LINE Developer account and obtain the necessary credentials.

4. Configure your environment variables with the LINE credentials.

### Running the Application

To run the application, you need to install kubernetes and minikube, and use kubernetes to deploy all service:
    ```sh
    kubectl create secret generic line-bot-secrets --from-literal=CHANNEL_ACCESS_TOKEN=YOUR_ACCESS_TOKEN --from-literal=CHANNEL_SECRET=YOUR_CHANNEL_SECRET 
    gcloud components install gke-gcloud-auth-plugin
    gcloud container clusters create my-cluster --enable-autoscaling --min-nodes=3 --max-nodes=5
    gcloud container clusters get-credentials my-cluster
    kubectl config current-context
    kubectl get nodes
    kubectl apply -f k8s/
    ```

### Lighter (Easier) Approach

To run the application with a lower cost, you can use Google Cloud Functions by transforming all code in each service to main function and send_reminder function, and deploy it on GCP.
    ```sh
    gcloud functions deploy linebot_function \                        
    --runtime python39 \
    --trigger-http \
    --entry-point linebot \
    --allow-unauthenticated \
    --set-env-vars CHANNEL_ACCESS_TOKEN=YOUR_ACCESS_TOKEN,CHANNEL_SECRET=YOUR_CHANNEL_SECRET \
    --gen2
    ```