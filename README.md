# GameServerController

A Discord bot to control multiple game servers running in Docker containers on an Unraid server. Start, stop, and check the status of game servers directly from Discord, with automatic shutdown after inactivity.

## Features

- **Multi-Game Support**: Manage multiple game servers via `config.json`.
- **Discord Commands**: Start (`!startserver`), stop (`!stopserver`), and check status (`!serverstatus`).
- **Auto Shutdown**: Automatically stops servers after inactivity.
- **Player Monitoring**: Monitors player connections/disconnections.

## Prerequisites

- **Unraid Server** with Docker.
- **Docker Access**: Bot requires access to the Docker daemon via socket.
- **Discord Bot**: With necessary permissions.
- **Game Server Containers**: Running in Docker.
- **Python 3.8+** (if not using Docker).

## Setup Instructions

1.  **Clone Repository**:

    git clone https://github.com/blueberryduck/gameservercontroller.git

2.  **Create Discord Bot**:

    - Go to [Discord Developer Portal](https://discord.com/developers/applications).
    - Create a new application and add a bot.
    - Copy the bot token (keep it secure).
    - Enable **"Message Content Intent"** under **"Privileged Gateway Intents"**.

3.  **Create `config.json`**:

    Create a `config.json` file with your game configurations:

        {
          "Palworld": {
            "container_name": "Palworld",
            "player_join_regex": "\\[.*\\] \\[LOG\\] (?P<player_name>.+?) joined the server\\. \\(User id: .*\\)",
            "player_leave_regex": "\\[.*\\] \\[LOG\\] (?P<player_name>.+?) left the server\\. \\(User id: .*\\)",
            "inactivity_limit": 600,
            "check_interval": 60
          },
          "OtherGame": {
            "container_name": "OtherGameContainer",
            "player_join_regex": "Player (?P<player_name>.+?) has joined the game",
            "player_leave_regex": "Player (?P<player_name>.+?) has left the game",
            "inactivity_limit": 300,
            "check_interval": 30
          }
        }

    - Customize configurations for your games.
    - Add new games as needed.

4.  **Build Docker Image**:

    docker build -t gameservercontroller .

5.  **Run Docker Container**:

        docker run -d \
          -v /var/run/docker.sock:/var/run/docker.sock \
          -e BOT_TOKEN=your_discord_bot_token \
          -e GAME_NAME=YourGameName \
          --name gameservercontroller \
          gameservercontroller

    - Replace `your_discord_bot_token` with your actual Discord bot token.
    - Replace `YourGameName` with the game name as specified in `config.json` (e.g., `Palworld`).

6.  **Invite Bot to Discord Server**:

    - Go to **"OAuth2"** > **"URL Generator"** in the Discord Developer Portal.
    - Select **"bot"** under **Scopes**.
    - Under **Bot Permissions**, check **"Send Messages"** and **"Read Message History"**.
    - Copy the generated URL and paste it into your browser.
    - Select your Discord server and authorize the bot.

## Usage

- **Commands**:

  - `!startserver`: Starts the game server.
  - `!stopserver`: Stops the game server.
  - `!serverstatus`: Shows server status.
  - `!help`: Displays help information.

- **Note**: Commands affect the game specified by the `GAME_NAME` environment variable.

## Customization

- **Add New Games**: Update `config.json` with new game configurations.
- **Adjust Inactivity Settings**: Modify `inactivity_limit` and `check_interval` in `config.json`.
- **Allowed Channels**: Update the `ALLOWED_CHANNELS` list in the bot script (`bot.py`):

       ALLOWED_CHANNELS = ['bot-commands', 'your-other-channel']

- **Log Parsing**: Adjust regex patterns in `config.json` to match your game server's log format.

## Security Considerations

- **Docker Socket Access**: Grants significant permissions; ensure the bot code is secure.
- **Restrict Bot Commands**: Limit to specific channels or user roles.
- **Protect Bot Token**: Keep your Discord bot token confidential.
- **Secure `config.json`**: If it contains sensitive information, secure it appropriately.

## Troubleshooting

- **Configuration Errors**: Ensure `config.json` is correctly formatted and includes all necessary configurations.
- **Environment Variables**: Verify that `BOT_TOKEN` and `GAME_NAME` are set correctly.
- **Docker Access**: Check that the Docker socket is correctly mounted and accessible.
- **Discord Permissions**: Ensure the bot has the necessary permissions in your Discord server.

## License

[MIT License](LICENSE)
