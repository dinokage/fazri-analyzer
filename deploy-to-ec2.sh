#!/bin/bash

INSTANCE_ID="i-091d1dcb0c1358f59"
APP_CONTAINER_NAME="nextjs-app"
# FIXED: Added /frontend to match build job
APP_CONTAINER_IMAGE="$CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHORT_SHA"

DOCKER_LOGIN_COMMAND="echo $CI_REGISTRY_PASSWORD | docker login $CI_REGISTRY -u $CI_REGISTRY_USER --password-stdin"
DOCKER_PULL_COMMAND="docker pull $APP_CONTAINER_IMAGE"

# Stop and remove old container
CONTAINER_STOP_COMMAND="if [ \$(docker ps -q -f name=$APP_CONTAINER_NAME) ]; then docker stop $APP_CONTAINER_NAME && docker rm $APP_CONTAINER_NAME; fi"

# Create network if it doesn't exist
NETWORK_CREATE_COMMAND="docker network create backend_fazri-network || true"

# Start container with network connection
CONTAINER_START_COMMAND="docker run -d --restart unless-stopped \
  --network backend_fazri-network \
  -p 3000:3000 \
  -e NEXTAUTH_URL='$NEXTAUTH_URL' \
  -e NEXTAUTH_SECRET='$NEXTAUTH_SECRET' \
  -e AUTH_GOOGLE_ID='$AUTH_GOOGLE_ID' \
  -e AUTH_GOOGLE_SECRET='$AUTH_GOOGLE_SECRET' \
  -e DATABASE_URL='$DATABASE_URL' \
  --name $APP_CONTAINER_NAME $APP_CONTAINER_IMAGE"

# Verify container is running
CONTAINER_VERIFY_COMMAND="docker ps | grep $APP_CONTAINER_NAME || (echo 'Container not running!' && docker logs $APP_CONTAINER_NAME && exit 1)"
CONTAINER_LOGS_COMMAND="docker logs --tail 30 $APP_CONTAINER_NAME"

echo "Deploying image: $APP_CONTAINER_IMAGE"

# Send commands to EC2
COMMAND_ID=$(aws ssm send-command \
    --document-name "AWS-RunShellScript" \
    --targets "Key=instanceIds,Values=$INSTANCE_ID" \
    --parameters commands="[\"$DOCKER_LOGIN_COMMAND\", \"$DOCKER_PULL_COMMAND\", \"$CONTAINER_STOP_COMMAND\", \"$NETWORK_CREATE_COMMAND\", \"$CONTAINER_START_COMMAND\", \"sleep 5\", \"$CONTAINER_VERIFY_COMMAND\", \"$CONTAINER_LOGS_COMMAND\"]" \
    --query "Command.CommandId" \
    --output text)

echo "Command sent. Command ID: $COMMAND_ID"

# Wait for completion
while true; do
    STATUS=$(aws ssm list-command-invocations \
        --command-id "$COMMAND_ID" \
        --details \
        --query "CommandInvocations[0].Status" \
        --output text)
    
    echo "Current Status: $STATUS"
    
    if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" || "$STATUS" == "TimedOut" || "$STATUS" == "Cancelled" ]]; then
        break
    fi
    sleep 2
done

OUTPUT=$(aws ssm list-command-invocations \
    --command-id "$COMMAND_ID" \
    --details \
    --query "CommandInvocations[0].CommandPlugins[0].Output" \
    --output text)

echo "Final Output:"
echo "$OUTPUT"

if [[ "$STATUS" == "Success" ]]; then
    echo "Docker command executed successfully."
    exit 0
else
    echo "Docker command failed with status: $STATUS"
    exit 1
fi