#!/bin/sh

set -eu

# Lowercase job status
JOB_STATUS=$(echo "${JOB_STATUS}" | tr '[:upper:]' '[:lower:]')
SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
CHANNEL=${CHANNEL}


AUTHOR=${GITHUB_ACTOR}
REPOSITORY=$GITHUB_REPOSITORY
RUN_ID=$GITHUB_RUN_ID
HEROKU_APP_NAME=${APP_ORIGIN}-pr-${PR_NUMBER}

slackMsg() {
    title=$1
    color=$2
    SLACK_MESSAGE="Deploying $HEROKU_APP_NAME failed \n $HEROKU_APP_NAME status = $title \n User = $AUTHOR"
    msg="{\"channel\":\"$CHANNEL\", \"as_user\":\"true\", \"attachments\": [ { \"title\":\"$SLACK_MESSAGE\", \"text\": \"$PR_URL https://github.com/$REPOSITORY/actions/runs/$RUN_ID https://dashboard.heroku.com/apps/$HEROKU_APP_NAME/logs\", \"color\": \"$color\" } ]}"

    curl -X POST \
    -H "Content-type: application/json" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -d "$msg" \
    https://slack.com/api/chat.postMessage
}

DatadogMsg() {
    EVENT_TITLE="Deploying $HEROKU_APP_NAME failed"
    EVENT_TEXT="Github Action= https://github.com/$REPOSITORY/actions/runs/$RUN_ID"
    TAGS="['app:${HEROKU_APP_NAME}','env:review-env']"
    curl  -X POST -H "Content-type: application/json" \
    -d '{
      "title": "'"${EVENT_TITLE}"'",
      "text": "'"${EVENT_TEXT}"'",
      "priority": "normal",
      "tags": "'"${TAGS}"'",
      "alert_type": "'"${EVENT_ALERT_TYPE}"'",
      "source_type_name": "GITHUB"
    }' \
    "https://api.datadoghq.com/api/v1/events?api_key=${DATADOG_API_KEY}"
}

if [ "$JOB_STATUS" = 'failure' ]; then
    slackMsg "FAILURE" "#FF0000"
    DatadogMsg 
fi