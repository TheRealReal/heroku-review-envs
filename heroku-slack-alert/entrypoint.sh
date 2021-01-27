#!/usr/bin/env bash

set -eu

<<COMMENT
export_env_dir() {
  # from https://devcenter.heroku.com/articles/buildpack-api#bin-compile
  env_dir=$1
  whitelist_regex=${2:-''}
  blacklist_regex=${3:-'^(PATH|GIT_DIR|CPATH|CPPATH|LD_PRELOAD|LIBRARY_PATH)$'}
  if [ -d "$env_dir" ]; then
    for e in $(ls $env_dir); do
      echo "$e" | grep -E "$whitelist_regex" | grep -qvE "$blacklist_regex" &&
      export "$e=$(cat $env_dir/$e)"
      :
    done
  fi
}
COMMENT

# Lowercase job status
JOB_STATUS=$(echo "$1" | tr '[:upper:]' '[:lower:]')
SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
CHANNEL=$2

AUTHOR=${GITHUB_ACTOR}
REPOSITORY=$GITHUB_REPOSITORY
RUN_ID=$GITHUB_RUN_ID

slackMsg() {
    title=$1
    color=$2
    SLACK_MESSAGE="*$HEROKU_APP_NAME* deployment status was $title\n>$AUTHOR\n\n\`\`\`\n$GITHUB_HEAD_REF"
    msg="{\"channel\":\"$CHANNEL\", \"attachments\": [ { \"title\":\"$SLACK_MESSAGE\", \"text\": "\"https://dashboard.heroku.com/apps/$HEROKU_APP_NAME\" \n\n \"https://dashboard.heroku.com/apps/$HEROKU_APP_NAME/logs\" \n\n \"https://github.com/$REPOSITORY/actions/runs/$RUN_ID\\"", \"color\": \"$color\" } ]}"
}

if [ "$JOB_STATUS" = 'failure' ]; then
    slackMsg "FAILURE" "#FF0000"
fi

curl -X POST \
-H "Content-type: application/json" \
-H "Authorization: Bearer $SLACK_BOT_TOKEN" \
-d "$msg" \
https://slack.com/api/chat.postMessage
