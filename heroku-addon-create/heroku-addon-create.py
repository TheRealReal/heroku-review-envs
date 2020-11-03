#!/usr/bin/env python3

import json
import os
import requests
import re
import sys
import time

# some constants
NEUTRAL_EXIT_CODE = 78

# tokens
HEROKU_TOKEN = os.environ['HEROKU_API_TOKEN']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

# basic headers for communicating with the Heroku API
HEADERS_HEROKU = {
    'Accept': 'application/vnd.heroku+json; version=3.review-apps',
    'Authorization': 'Bearer %s' % HEROKU_TOKEN,
    'User-Agent': 'Heroku GitHub Actions Provider by TheRealReal',
    'Content-Type': 'application/json'
    }
HEADERS_HEROKU_REVIEW_PIPELINES = {
    'Accept': 'application/vnd.heroku+json; version=3.pipelines',
    'Authorization': 'Bearer %s' % HEROKU_TOKEN,
    'User-Agent': 'Heroku GitHub Actions Provider by TheRealReal',
    'Content-Type': 'application/json'
    }

API_URL_HEROKU = 'https://api.heroku.com'

# basic headers for communicating with the GitHub API
HEADERS_GITHUB = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': 'token %s' % GITHUB_TOKEN,
    'User-Agent': 'Heroku GitHub Actions Provider by TheRealReal',
    'Content-Type': 'application/json'
    }
API_URL_GITHUB = 'https://api.github.com'

# Heroku Related Functions #####################################################

def get_review_app_by_branch( pipeline_id, branch_name ):
    r = requests.get(API_URL_HEROKU+'/pipelines/'+pipeline_id+'/review-apps', headers=HEADERS_HEROKU)
    reviewapps = json.loads(r.text)
    reviewapp = next((x for x in reviewapps if x['branch'] == branch_name), None)
    try:
        if reviewapp is not None and 'app' in reviewapp and 'id' in reviewapp['app']:
            return reviewapp
    except:
        pass
    return None

def get_app_by_name( app_name ):
    r = requests.get(API_URL_HEROKU+'/apps/'+app_name, headers=HEADERS_HEROKU)
    app = json.loads(r.text)
    try:
        if app is not None and 'id' in app:
            return app
    except:
        pass
    return None

def create_addon( app_name, addon_name, addon_plan, addon_config=None ):
    payload = {
        'plan': addon_plan,
        'attachment': {
            'name': addon_name
        }
    }
    if addon_config:
        payload['config'] = addon_config
    r = requests.post(API_URL_HEROKU+'/apps/'+app_name+'/addons', headers=HEADERS_HEROKU_REVIEW_PIPELINES, data=json.dumps(payload))
    return json.loads(r.text)

def attach_addon( app_name, addon_name, addon_id ):
    payload = {
        'addon': addon_id,
        'app': app_name,
        'name': addon_name
    }
    r = requests.post(API_URL_HEROKU+'/addon-attachments', headers=HEADERS_HEROKU_REVIEW_PIPELINES, data=json.dumps(payload))
    return json.loads(r.text)

def get_app_addon_attachments( app_name ):
    r = requests.get(API_URL_HEROKU+'/apps/'+app_name+'/addon-attachments', headers=HEADERS_HEROKU_REVIEW_PIPELINES)
    addons = json.loads(r.text)
    return addons

# GitHub Related Functions #####################################################

def get_latest_commit_for_branch( repo, branch_name ):
    r = requests.get(API_URL_GITHUB+'/repos/'+repo+'/branches/'+branch_name, headers=HEADERS_GITHUB)
    branch = json.loads(r.text)
    try:
        return branch['commit']['sha']
    except:
        return None

def get_pr_name( repo, branch_name, page=1 ):
    r = requests.get(API_URL_GITHUB+'/repos/'+repo+'/pulls?state=all&page='+str(page)+'&per_page=100', headers=HEADERS_GITHUB)
    prs = json.loads(r.text)
    pr = next((x for x in prs if x['head']['ref'] == branch_name), None)
    if pr:
        return pr
    else:
        return get_pr_name( repo, branch_name, page=page+1)

def add_pr_comment( repo, pr_id, message):
    payload = {
        'body': message
    }
    r = requests.post(API_URL_GITHUB+'/repos/'+repo+'/issues/'+str(pr_id)+'/comments', headers=HEADERS_GITHUB, data=json.dumps(payload))
    comment = json.loads(r.text)
    return comment


# Non-API-Related Functions ####################################################

def get_app_name( svc_origin, svc_name, pr_num, prefix ):
    if svc_origin != svc_name:
        # if related app, we append the app name
        name = "%s-%s-pr-%s-%s" % ( prefix, svc_origin, pr_num, svc_name )
    else:
        # if this is the originating app, just name it like vanilla review apps
        name = "%s-%s-pr-%s" % ( prefix, svc_origin, pr_num )
    # truncate to 30 chars for Heroku
    return name[:30]


# PROCESS ENV and ARGS #########################################################

print ("Start "+sys.argv[0])
def mask( k, v ):
    if 'TOKEN' in k or 'SECRET' in k:
        return '***'
    else:
        return v
print ("Environment: " + str({k: mask(k,v) for k, v in os.environ.items()}))

# get the github event json
if 'GITHUB_EVENT_PATH' in os.environ:
    EVENT_FILE = os.environ['GITHUB_EVENT_PATH']
    with open(EVENT_FILE, 'r', encoding="utf-8") as eventfile:
        GH_EVENT = json.load(eventfile)

# support arguments passed in via the github actions workflow via the syntax
# args = ["HEROKU_PIPELINE_NAME=github-actions-test"]
args = {}
for arg in sys.argv:
    pair = arg.split('=')
    if len(pair) > 1:
        args[pair[0]] = '='.join(pair[1:])
    else:
        args[arg] = arg

# for quick testing, we want these to be alternatively passed in via environment
args_or_envs = [
    'HEROKU_TEAM_NAME',
    'APP_PREFIX',
    'APP_ORIGIN',
    'APP_NAME',
    'RELATED_APPS',
    'ADDON_PLAN',
    'ADDON_NAME',
    'REQUIRE_LABEL'
]
for i in args_or_envs:
    if i not in args and i in os.environ:
        args[i] = os.environ[i]

print ("Found arguments: " + str( {k: v for k, v in args.items() if 'TOKEN' not in k and 'SECRET' not in k} ))

# GET THE INPUTS SET UP RIGHT ##################################################

# determine the app_short_name - short name that references the type of service
app_short_name = args['APP_NAME']
print ("Service Name: "+app_short_name)

# APP_ORIGIN is the originating app. Fill in the value of this var just for ease of use.
app_origin = app_short_name
if 'APP_ORIGIN' in args:
    app_origin = args['APP_ORIGIN']
    # if required transform origin repo name into origin app name
    if app_origin == "real-server":
        app_origin = "web"
    if app_origin == "inventory-service":
        app_origin = "inventory"
print("Originating Service: "+app_origin)

# pull branch name from the GITHUB_REF
try:
    branch_origin = GH_EVENT['pull_request']['head']['ref'] # this has been more reliable
except:
    branch_origin = os.environ['GITHUB_REF'][11:] # this is sometimes wrong
commit_sha = os.environ['GITHUB_SHA']
origin_commit_sha = commit_sha

# set the app name prefix properly
app_prefix = args['APP_PREFIX']

# we always need to know the originating repo:
repo_origin = os.environ['GITHUB_REPOSITORY']

# Require a pull request label to be present
require_label = args['REQUIRE_LABEL'] if 'REQUIRE_LABEL' in args.keys() else False

# we are always deploying this using information from the origin app
repo = repo_origin
branch = branch_origin

github_org = repo.split('/')[0]
print ("GitHub Org: "+github_org)
print ("Repo: "+repo)
print ("Branch to deploy: "+branch)

# DETERMINE THE APP NAME #######################################################

try:
    # we expect that the event payload has a pull_request object at the first level
    pr = GH_EVENT['pull_request']
except:
    try:
        # look up the PR number for origin repo
        pr = get_pr_name( repo_origin, branch_origin )
    except Exception as ex:
        print(ex)
        sys.exit("Couldn't find a PR for this branch - " + repo_origin + '@' + branch_origin)

pr_num = pr['number']
pr_labels = [x['name'] for x in pr['labels']]
pr_status = pr['state']
print ("Found Pull Request: \"" + pr['title'] + "\" id: " + str(pr_num))

# check required PR label
print ("Detected Labels: " + ', '.join(pr_labels))
if require_label:
    print ("Required Labels: " + require_label)
    if require_label not in pr_labels:
        print ("To spin up this add-on, label your pr with "+require_label)
        sys.exit( NEUTRAL_EXIT_CODE )
else:
    print ("Skipping label check")

# determine the app_name
app_name = get_app_name( app_origin, app_short_name, pr_num, app_prefix )

print ("App Name: "+app_name)

# START CREATING/DEPLOYING #####################################################

# see if there's a review app for this branch already
app = get_app_by_name( app_name )

app_id = None
if app is not None:
    app_id = app['id']
    print ("Found originating app id: " + app_id )

    # check existing addon attachments
    addon_attachments = get_app_addon_attachments( app_name )
    addon = next((x['addon'] for x in addon_attachments if x['name'] == args['ADDON_NAME']), None)

    if addon:
        # no action necessary
        print("Addon %s (%s) has already been added to %s as %s." % (addon['name'], args['ADDON_PLAN'], app_name, args['ADDON_NAME'] ))

    else:
        # spin up the addon for this app
        print ("Creating an addon plan = %s for app %s as %s..." % ( args['ADDON_PLAN'], app_name, args['ADDON_NAME'] ))
        addon = create_addon( app_name, args['ADDON_NAME'], args['ADDON_PLAN'] )
        print(json.dumps(addon, sort_keys=True, indent=4))
        if 'name' not in addon:
            sys.exit("Couldn't create the addon.")

    # attach the addon to apps
    if "RELATED_APPS" in args:
        app_short_names = list(filter(None, args['RELATED_APPS'].split(',')))
        print ("Attaching %s (%s) addon as %s to multiple apps: %s" % (addon['name'], args['ADDON_PLAN'], args['ADDON_NAME'], ','.join(app_short_names)))

        for attach_app_shortname in app_short_names:
            attach_app_name = get_app_name( app_origin, attach_app_shortname, pr_num, app_prefix )
            existing_app_addons = get_app_addon_attachments( attach_app_name )
            existing_app_addon = next((x for x in existing_app_addons if type(x) is dict and x['name'] == args['ADDON_NAME']), None)
            if existing_app_addon:
                print ("App %s already has addon %s (%s) attached as %s." % (attach_app_name, addon['name'], args['ADDON_PLAN'], args['ADDON_NAME']))
            else:
                print ("Attaching addon %s (%s) to %s as %s..." % (addon['name'], args['ADDON_PLAN'], attach_app_name, args['ADDON_NAME']))
                attachment = attach_addon( attach_app_name, args['ADDON_NAME'], addon['name'] )
                if 'name' not in attachment:
                    sys.exit("Couldn't attach addon %s (%s) to app %s as %s" % (addon['name'], args['ADDON_PLAN'], attach_app_name, args['ADDON_NAME'] ))

else:
    sys.exit("Found no existing app: %s." % app_name)

print ("Done.")
