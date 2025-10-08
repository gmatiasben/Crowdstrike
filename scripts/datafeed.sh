#!/bin/bash

# Stream API connection SIEM emulation
# Matias Bendel 2025

# Set your credentials
CLIENT_ID="FILL-ME"
CLIENT_SECRET="FILL-ME"
APP_ID="my-test-app-000"

# Get token
echo "Getting authentication token..."
TOKEN=$(curl -s -X POST "https://api.crowdstrike.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID&client_secret=$CLIENT_SECRET" | jq -r '.access_token')

#DEBUG
#echo "Access token: $TOKEN"

# Create stream
echo "Creating event stream..."
STREAM_RESPONSE=$(curl -s -X GET "https://api.crowdstrike.com/sensors/entities/datafeed/v2?appId=$APP_ID&eventType=DetectionSummaryEvent" \
  -H "Authorization: Bearer $TOKEN")

#DEBUG
#echo "Stream Response: $STREAM_RESPONSE"

# Extract the correct values
SESSION_TOKEN=$(echo "$STREAM_RESPONSE" | jq -r '.resources[0].sessionToken.token')
STREAM_URL=$(echo "$STREAM_RESPONSE" | jq -r '.resources[0].dataFeedURL')
REFRESH_URL=$(echo "$STREAM_RESPONSE" | jq -r '.resources[0].refreshActiveSessionURL')
REFRESH_INTERVAL=$(echo "$STREAM_RESPONSE" | jq -r '.resources[0].refreshActiveSessionInterval')
CLOSE_URL=$(echo "$REFRESH_URL" | sed 's/refresh_active_stream_session/close_stream_session/g')

echo "Session token: $SESSION_TOKEN"
echo "Stream URL: $STREAM_URL"
echo "Refresh URL: $REFRESH_URL"
echo "Refresh interval: $REFRESH_INTERVAL seconds"

# Get events
echo "Getting events..."
curl -s -X GET "$STREAM_URL" \
  -H "Accept: application/json" \
  -H "Authorization: Token $SESSION_TOKEN"

# Refresh stream
#echo "Refreshing stream..."
#curl -s -X POST "$REFRESH_URL" \
#  -H "Authorization: Bearer $TOKEN" \
#  -H "Content-Type: application/json"

# Close stream when done
#echo "Closing stream..."
#curl -s -X POST "$CLOSE_URL" \
#  -H "Authorization: Bearer $TOKEN" \
#  -H "Content-Type: application/json"
