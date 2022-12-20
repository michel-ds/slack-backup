#!/usr/bin/python3
# Code initially based on
# https://gist.github.com/benoit-cty/a5855dea9a4b7af03f1f53c07ee48d3c
# This code, adapted from https://github.com/edemaine/slack-backup

import urllib.request, urllib.parse
import os
import json
import bz2
from datetime import datetime

import boto3

TOKEN = os.environ['TOKEN']  # provide bot or user token (preferably user)
FILE_TOKEN = os.environ.get('FILE_TOKEN')  # file access token via public dump
DOWNLOAD = os.environ.get('DOWNLOAD')
STORAGE_LOC = os.environ.get('STORAGE_LOC')

BACKUP = '/tmp/backup'
os.makedirs(BACKUP, mode=0o700, exist_ok=True)

REGION = "eu-west-1"
PROFILE = os.environ.get('PROFILE')
SESSION = boto3.Session(region_name=REGION, profile_name=PROFILE)



# Import Slack Python SDK (https://github.com/slackapi/python-slack-sdk)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=TOKEN)
indent = 0

def slack_list(field, info, operation, **dargs):
  # Most WebClient methods are paginated, returning the first n results
  # along with a "next_cursor" pointer to fetch the rest.
  print(f'{" " * indent}Fetching {info or field}...')
  try:
    items = []
    cursor = None
    while True:
      result = operation(cursor=cursor, **dargs)
      items += result[field]
      if 'response_metadata' not in result: break
      cursor = result['response_metadata']['next_cursor']
      if not cursor: break
      print(f'{" " * indent}  Fetching more...')
    print(f'{" " * indent}  Fetched {len(items)} {field}')
  except SlackApiError as e:
    print("ERROR USING CONVERSATION: {}".format(e))
  return items

def all_channels():
  return slack_list('channels', 'all channels',
    client.conversations_list, types='public_channel, private_channel')

def all_channel_members(channel):
  return slack_list('members', f'all members in channel {channel["name"]}',
    client.conversations_members, channel=channel['id'])

def all_channel_messages(channel):
  return slack_list('messages', f'all messages from channel {channel["name"]}',
    client.conversations_history, channel=channel['id'])

def all_users():
  return slack_list('members', 'all users', client.users_list)


def save_json(data, filename, compress=True):
  os.makedirs(os.path.dirname(filename), mode=0o700, exist_ok=True)
  if compress:
    filename = f"{filename}.bz2"
    print('  Saving to', filename)
    with bz2.open(filename, "wb") as outfile:
      # Write compressed data to file
      json_str = json.dumps(data, indent=2) + "\n"
      json_bytes = json_str.encode('utf-8')
      outfile.write(json_bytes)
  else:
    print('  Saving to', filename)
    with open(filename, 'w') as outfile:
      json.dump(data, outfile, indent=2)
  return filename


def backup_channel(channel):
  try:
    all_messages = all_channel_messages(channel)
    filename = f'{BACKUP}/{channel["name"]}/all.json'
    filename = save_json(all_messages, filename)

    # Rewrite private URLs to have token, like Slack's public dump
    filenames = {'all.json'}  # avoid overwriting json
    count = 0
    for message in all_messages:
      if 'files' in message:
        for file in message['files']:
          count += 1
          for key, value in list(file.items()):
            if (key.startswith('url_private') or key.startswith('thumb')) \
               and isinstance(value, str) and value.startswith('https://'):
              if FILE_TOKEN:
                file[key] = value + '?t=' + FILE_TOKEN
              if DOWNLOAD and not key.endswith('_download'):
                filename = os.path.basename(urllib.parse.urlparse(value).path)
                if filename in filenames:
                  i = 0
                  base, ext = os.path.splitext(filename)
                  def rewrite():
                    return base + '_' + str(i) + ext
                  while rewrite() in filenames:
                    i += 1
                  filename = rewrite()
                filenames.add(filename)
                # https://api.slack.com/types/file#authentication
                with urllib.request.urlopen(urllib.request.Request(value,
                       headers={'Authorization': 'Bearer ' + TOKEN})) as infile:
                  with open(f'{BACKUP}/{channel["name"]}/{filename}', 'wb') as outfile:
                    outfile.write(infile.read())
                file[key + '_file'] = f'{channel["name"]}/{filename}'
    verbs = []
    if DOWNLOAD: verbs.append('Downloaded')
    if FILE_TOKEN: verbs.append('Linked')
    if verbs: print(f'  {" & ".join(verbs)} {count} files from messages in {channel["name"]}.')
    if count and FILE_TOKEN:
      filename = save_json(all_messages, filename)

    return filename

  except SlackApiError as e:
      print("Error using conversation: {}".format(e))

def backup_all_channels():
  channels = all_channels()
  for channel in channels:
    channel['members'] = all_channel_members(channel)

  filename = f'{BACKUP}/channels.json'
  filename = save_json(channels, filename)
  channel_names = []
  for channel in channels:
    channel_names.append(backup_channel(channel))
  return [filename] + channel_names

def backup_all_users():
  users = all_users()
  return save_json(users, f'{BACKUP}/users.json')

def ship_to_storage(storage_loc, *args):
  s3 = SESSION.resource("s3")
  my_bucket = s3.Bucket(storage_loc)
  target_folder = datetime.now().isoformat()
  for path in args:
    filename = os.path.join(*filter(lambda x: x not in BACKUP.split('/'), path.split('/')))
    ## Upload file
    my_bucket.upload_file(path, f"{target_folder}/{filename}")
    print(f"Uploaded {filename}.")

def main(event=None, context=None):
  users_loc = backup_all_users()
  channels_loc = backup_all_channels()
  ship_to_storage(STORAGE_LOC, users_loc, *channels_loc)


if __name__ == "__main__":
  main()