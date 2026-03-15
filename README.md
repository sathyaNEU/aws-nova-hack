# start fastapi server
uvicorn app:app --reload --port 3000

# start ngrok http tunnel
ngrok http 3000

# start slack webhook server
uvicorn slack_webhook:app --port 8000

# start ngrok http tunnel
ngrok http 8000

# ECS deployment
- aws ecr get-login-password --region us-east-1 --profile dev-pers | docker login --username AWS --password-stdin 374834463497.dkr.ecr.us-east-1.amazonaws.com
- docker build -t sonic-serve .
- docker tag sonic-serve:latest 374834463497.dkr.ecr.us-east-1.amazonaws.com/aws-nova-hack:latest
- docker push 374834463497.dkr.ecr.us-east-1.amazonaws.com/aws-nova-hack:latest
- aws ecs update-service --cluster default --service aws-nova-hack-dd04 --force-new-deployment --region us-east-1 --profile dev-pers
