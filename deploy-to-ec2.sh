#!/bin/bash

INSTANCE_ID="i-091d1dcb0c1358f59"
APP_CONTAINER_NAME="nextjs-app"
APP_CONTAINER_IMAGE="$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA"

DOCKER_LOGIN_COMMAND="echo $CI_REGISTRY_PASSWORD | docker login $CI_REGISTRY -u $CI_REGISTRY_USER --password-stdin"
DOCKER_PULL_COMMAND="docker pull $APP_CONTAINER_IMAGE"

# Stop and remove old container
CONTAINER_STOP_COMMAND="if [ \$(docker ps -q -f name=$APP_CONTAINER_NAME) ]; then docker stop $APP_CONTAINER_NAME && docker rm $APP_CONTAINER_NAME; fi"

# Start container with all environment variables
CONTAINER_START_COMMAND="docker run -d --restart unless-stopped -p 80:3000 \
  -e NEXTAUTH_URL='$NEXTAUTH_URL' \
  -e NEXTAUTH_SECRET='$NEXTAUTH_SECRET' \
  -e AUTH_GOOGLE_ID='$AUTH_GOOGLE_ID' \
  -e AUTH_GOOGLE_SECRET='$AUTH_GOOGLE_SECRET' \
  -e DATABASE_URL='$DATABASE_URL' \
  --name $APP_CONTAINER_NAME $APP_CONTAINER_IMAGE"

echo "Deploying image: $APP_CONTAINER_IMAGE"

# Send commands to EC2
COMMAND_ID=$(aws ssm send-command \
    --document-name "AWS-RunShellScript" \
    --targets "Key=instanceIds,Values=$INSTANCE_ID" \
    --parameters commands="[\"$DOCKER_LOGIN_COMMAND\", \"$DOCKER_PULL_COMMAND\", \"$CONTAINER_STOP_COMMAND\", \"$CONTAINER_START_COMMAND\"]" \
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

# Get output
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