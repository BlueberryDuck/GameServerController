# GameServerController

A Discord bot that allows users to control a game server running in a Docker container on an Unraid server. The bot can start, stop, and check the status of the game server, and it automatically shuts down the server after a period of inactivity.

## Features

- **Start the Game Server**: Start your game server directly from Discord.
- **Stop the Game Server**: Stop the game server when not in use.
- **Server Status**: Check if the game server is running.
- **Auto Shutdown**: Automatically stops the game server after 10 minutes of inactivity.
- **Player Activity Monitoring**: Monitors player connections and disconnections in real-time.

## Prerequisites

- **Unraid Server**: Running Docker containers.
- **Docker Access**: The bot needs access to the Docker daemon via the Docker socket.
- **Discord Account**: With permissions to add bots to your Discord server.
- **Game Server Docker Container**: Your game server should be running in a Docker container.

## Setup Instructions

### 1. Clone the Repository

Clone this repository to your Unraid server:

    git clone https://github.com/blueberryduck/gameservercontroller.git
    cd gameservercontroller

### 2. Create a Discord Bot

1. **Discord Developer Portal**: Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. **New Application**: Click on **"New Application"**, give it a name, and create it.
3. **Add a Bot**: Navigate to the **"Bot"** tab and click **"Add Bot"**.
4. **Bot Token**: Click **"Reset Token"** and copy the token. **Keep it secure!**
5. **Enable Intents**: Under **"Privileged Gateway Intents"**, enable **"Message Content Intent"**.

### 3. Build the Docker Image

Build the Docker image for the bot:

    docker build -t gameservercontroller .

### 4. Run the Docker Container

Run the bot's Docker container with the Docker socket mounted and BOT_TOKEN set:

### 5. Invite the Bot to Your Discord Server

1. **OAuth2 URL Generator**: In the Discord Developer Portal, go to **"OAuth2"** > **"URL Generator"**.
2. **Scopes**: Select **"bot"**.
3. **Bot Permissions**: Check **"Send Messages"** and **"Read Message History"**.
4. **Generate URL**: Copy the generated URL.
5. **Invite the Bot**: Paste the URL into your browser, select your server, and authorize the bot.

## Usage

### Bot Commands

- `!startserver`: Starts the game server.
- `!stopserver`: Stops the game server.
- `!serverstatus`: Shows the current status of the game server.
- `!help`: Displays help information about the bot commands.

### Monitoring Player Activity

The bot automatically monitors player activity by streaming the game server's logs in real-time. It will shut down the server after the specified period of inactivity.

## Customization

### Adjusting Inactivity Settings

- **Inactivity Limit**: Modify `INACTIVITY_LIMIT` to adjust how long the server waits before shutting down due to inactivity.
- **Check Interval**: Modify `CHECK_INTERVAL` to change how frequently the bot checks for player activity.

### Allowed Channels

Update `ALLOWED_CHANNELS` to specify which Discord channels the bot listens to for commands.

### Log Parsing

If your game server's log format differs, adjust the regular expressions in `bot.py` to correctly parse player join and leave events.

## Security Considerations

- **Docker Socket Access**: The bot requires access to the Docker socket, which grants significant permissions. Ensure the bot's code is secure and that access is restricted.
- **Restrict Bot Commands**: The bot only responds in specified channels. Consider further restricting commands to certain users or roles.
- **Protect Your Bot Token**: Never share your Discord bot token. Store it securely and avoid hardcoding it in your scripts.

## Logging

- The bot uses Python's `logging` module.
- Logs are output to the console and can be viewed using Docker logs
