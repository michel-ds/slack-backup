# slack-backup

This Python script downloads a backup of all Slack users, all channels
(*including private channels*), and all messages in those channels.
The produced dump is in the same format produced by an
[official Slack export of workspace data](https://slack.com/help/articles/201658943-Export-your-workspace-data)
(which works well for public channels but not private channels).
The data dumps are then uploaded to a remote storage (AWS S3) location.

The intended use-case for preserving messages that are older than 90 days because of Slack's [change in limits to the free plan](https://slack.com/help/articles/7050776459923-Pricing-changes-for-the-Pro-plan-and-updates-to-the-Free-plan).

## Usage

### Running slack-backup

1. Clone this repository.
2. Install Python 3 if needed.
3. `pip install slack_sdk`
4. [Create a Slack app](https://api.slack.com/apps/new)
5. Under OAuth &amp; Permissions, in the User Token Scopes section
   (I've found the user token to work better than the bot token, but YMMV),
   add the following scopes:

   * `admin` (not sure whether this is necessary)
   * `channels:history`
   * `channels:read`
   * `files:read`
   * `groups:history`
   * `groups:read`
   * `users:read`
   * `users:read.email`

   Also write down the Bot User OAuth Token.
   (These directions are based on
   [this documentation](https://github.com/docmarionum1/slack-archive-bot).)
6. Under Install App, be sure to install the bot to the workspace
   you'd like to backup.
7. Assuming you're using the User Token, be sure that you have been added to
   all private channels that you want to backup.  (Even admins/owners cannot
   see all private channels in the channel list; they need to be invited.)
   If you're using the Bot User Token, you probably need to invite the bot
   to all desired channels.
8. ~~I recommend also running an
   [official Slack export of workspace data](https://slack.com/help/articles/201658943-Export-your-workspace-data).
   In JSON files containing file uploads, you'll see URLs ending with
   `?t=xoxe-...`.  Write down that token too.
   (This is a temporary file access token; I think it lasts 7 days.)~~
9. Make sure you AWS credentials are up-to-date (you have write access to the remote storage)
10. Then I suggest creating a `run` script with the following contents:

   ```sh
   #!/bin/sh
   export TOKEN='xoxp-...'  # Bot User OAuth Token
   # Optional settings: (you can omit them)
   export FILE_TOKEN='xoxe-...'  # file access export token from previous step
   export DOWNLOAD=1  # download all message files locally too
   python slack_backup.py
   ```
10. Run the `run` script via `./run` and wait.
11. The output will be in a created `/tmp/backup` subdirectory and also upload the files to the remote storage.
12. To produce a `backup.zip` file in the same format as a Slack export,
    do the following in a shell (assuming you have `zip` installed):

    ```sh
    cd backup
    zip -9r ../backup.zip *
    ```

### Deploying the code as a lambda function

Please read [this article](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-create-package-with-dependency) if you don't know how to bundle up Python code for AWS Lambda functions.

In order to bundle up the code into a single archive that can then be deployed as Lambda function, run the following:  
```bash
pip install -r requirements.txt --target packages
./bundle.sh
```

We use a different function name to be invoked, called **main()**.

This will create a `my-deployment-package.zip` file that can then be uploaded as function archive.  
Note that AWS Lambda at the time of writing only supports Python **3.7** and **3.8**.


## History

This code was initially based on a
[gist](https://gist.github.com/benoit-cty/a5855dea9a4b7af03f1f53c07ee48d3c)
by [Benoit Courty](https://gist.github.com/benoit-cty).  
The fork ([original code](https://github.com/edemaine/slack-backup)) this repo is based on adds channel listing, user listing, file downloads, and
making the output format compatible with standard Slack dumps.

I, `@michel-ds`, have further added an upload to remote storage feature.