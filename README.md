# start fastapi server
uvicorn app:app --reload --port 3000

# start ngrok http tunnel
ngrok http 3000

# start slack webhook server
uvicorn slack_webhook:app --port 8000

# start ngrok http tunnel
ngrok http 8000