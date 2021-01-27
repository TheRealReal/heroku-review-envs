FROM curlimages/curl:7.68.0

LABEL "com.github.actions.name"="Heroku Failure Job status to Slack"
LABEL "com.github.actions.description"="Post workflow for Failure job status for a Review Environment"
LABEL "com.github.actions.icon"="box"
LABEL "com.github.actions.color"="purple"

LABEL "repository"="http://github.com/TheRealReal/heroku-review-envs"
LABEL "homepage"="http://github.com/TheRealReal/heroku-review-envs"
LABEL "maintainer"="The RealReal DevOps <devops@therealreal.com>"

ADD entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh 

ENTRYPOINT ["/entrypoint.sh"]
