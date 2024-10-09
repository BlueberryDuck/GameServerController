import json
import logging
import os
import re
import threading
import time

import discord
from discord.ext import commands, tasks
import docker

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to INFO or DEBUG for more verbosity
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Get the bot token and game name from environment variables
TOKEN = os.getenv("BOT_TOKEN")
GAME_NAME = os.getenv("GAME_NAME")
CHANNEL_NAME = os.getenv("CHANNEL_NAME")

if not TOKEN:
    logging.error("BOT_TOKEN environment variable not set.")
    exit(1)

if not GAME_NAME:
    logging.error("GAME_NAME environment variable not set.")
    exit(1)

# Load game configurations from config.json
CONFIG_FILE = "config.json"

try:
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error(f'Configuration file "{CONFIG_FILE}" not found.')
    exit(1)
except json.JSONDecodeError as e:
    logging.error(f"Error parsing configuration file: {e}")
    exit(1)

if GAME_NAME not in config:
    logging.error(f'Game "{GAME_NAME}" not found in configuration.')
    exit(1)

game_config = config[GAME_NAME]

# Extract game-specific settings
CONTAINER_NAME = game_config["container_name"]
INACTIVITY_LIMIT = game_config["inactivity_limit"]  # In seconds
CHECK_INTERVAL = game_config["check_interval"]  # In seconds

# Define the intents your bot will use
intents = discord.Intents.default()
intents.message_content = (
    True  # Allows the bot to read message content (necessary for commands)
)

# Initialize the bot with command prefix '!' and the specified intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize Docker client
docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")

class ServerManager:
    """
    Class to manage the server state and monitoring.
    """

    def __init__(self, game_config):
        self.game_config = game_config
        self.online_players = set()
        self.online_players_lock = threading.Lock()
        self.log_monitoring_thread = None
        self.inactivity_time = 0
        # Compile regex patterns
        self.player_join_pattern = re.compile(self.game_config["player_join_regex"])
        self.player_leave_pattern = re.compile(self.game_config["player_leave_regex"])

    def monitor_container_logs(self):
        """
        Monitor the Docker container logs for player join/leave events.
        """
        while True:
            try:
                container = docker_client.containers.get(CONTAINER_NAME)
                container.reload()
                if container.status != "running":
                    logging.info(
                        f'Container "{CONTAINER_NAME}" is not running. Retrying in 10 minutes...'
                    )
                    time.sleep(600)
                    continue

                logging.info(
                    f'Starting log monitoring for container "{CONTAINER_NAME}"'
                )
                # Stream logs in real-time
                log_stream = container.logs(
                    stream=True, follow=True, since=int(time.time())
                )

                for log in log_stream:
                    line = log.decode("utf-8").strip()
                    if not line:
                        continue
                    # Process the log line
                    match = self.player_join_pattern.match(line)
                    if match:
                        player = match.group("player_name")
                        with self.online_players_lock:
                            self.online_players.add(player)
                        logging.info(f"Player joined: {player}")
                        continue
                    match = self.player_leave_pattern.match(line)
                    if match:
                        player = match.group("player_name")
                        with self.online_players_lock:
                            self.online_players.discard(player)
                        logging.info(f"Player left: {player}")
            except docker.errors.NotFound:
                logging.warning(
                    f'Container "{CONTAINER_NAME}" not found. Retrying in 5 seconds...'
                )
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error in monitor_container_logs: {e}", exc_info=True)
                time.sleep(5)

    def start_log_monitoring_thread(self):
        """
        Start the thread to monitor container logs.
        """
        if (
            self.log_monitoring_thread is None
            or not self.log_monitoring_thread.is_alive()
        ):
            self.log_monitoring_thread = threading.Thread(
                target=self.monitor_container_logs, daemon=True
            )
            self.log_monitoring_thread.start()
            logging.info("Started log monitoring thread")

    def stop_log_monitoring_thread(self):
        """
        Stop the log monitoring thread.
        """
        # Daemon threads exit when main program exits; we don't need to do anything special here
        self.log_monitoring_thread = None
        logging.info("Stopped log monitoring thread")


server_manager = ServerManager(game_config)


def is_allowed(ctx):
    """
    Check if the command is allowed in the current channel.
    """
    return ctx.channel.name == CHANNEL_NAME


# Command to start the game server
@bot.command(
    name="startserver",
    help=(
        f"Starts the game server.\n\nUse this command to start the {GAME_NAME} game server. "
        "The server will begin monitoring player activity once started."
    ),
    brief="Starts the game server.",
)
async def start_server(ctx):
    if not is_allowed(ctx):
        return
    try:
        container = docker_client.containers.get(CONTAINER_NAME)
        container.reload()
        if container.status != "running":
            container.start()
            await ctx.send("Game server is starting!")
            # Start the log monitoring thread
            server_manager.start_log_monitoring_thread()
        else:
            await ctx.send("Game server is already running.")
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        logging.error(f"Error starting the server: {e}", exc_info=True)
        await ctx.send(f"Error starting the server: {e}")


# Command to stop the game server
@bot.command(
    name="stopserver",
    help=(
        f"Stops the game server.\n\nUse this command to stop the {GAME_NAME} game server. "
        "This will also stop the player activity monitoring."
    ),
    brief="Stops the game server.",
)
async def stop_server(ctx):
    if not is_allowed(ctx):
        return
    try:
        container = docker_client.containers.get(CONTAINER_NAME)
        container.reload()
        if container.status == "running":
            container.stop()
            await ctx.send("Game server is stopping!")
            # Stop the log monitoring thread
            server_manager.stop_log_monitoring_thread()
        else:
            await ctx.send("Game server is not running.")
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        logging.error(f"Error stopping the server: {e}", exc_info=True)
        await ctx.send(f"Error stopping the server: {e}")


# Command to check server status
@bot.command(
    name="serverstatus",
    help=(
        f"Displays the current status of the game server.\n\nShows whether the {GAME_NAME} game "
        "server is running or stopped."
    ),
    brief="Displays the game server status.",
)
async def server_status(ctx):
    if not is_allowed(ctx):
        return
    try:
        container = docker_client.containers.get(CONTAINER_NAME)
        container.reload()  # Refresh container state
        status = container.status  # 'running', 'exited', etc.
        await ctx.send(f"Game server status: {status}")
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        logging.error(f"Error retrieving server status: {e}", exc_info=True)
        await ctx.send(f"Error retrieving server status: {e}")


# Background task to monitor inactivity
@tasks.loop(seconds=CHECK_INTERVAL)
async def monitor_inactivity():
    """
    Background task to monitor inactivity and stop the server if necessary.
    """
    try:
        container = docker_client.containers.get(CONTAINER_NAME)
        container.reload()
        if container.status == "running":
            with server_manager.online_players_lock:
                players_online_count = len(server_manager.online_players)
            logging.info(f"Players online: {players_online_count}")
            if players_online_count > 0:
                server_manager.inactivity_time = 0
            else:
                server_manager.inactivity_time += CHECK_INTERVAL
                if server_manager.inactivity_time >= INACTIVITY_LIMIT:
                    container.stop()
                    logging.warning(
                        f"No players online for {INACTIVITY_LIMIT} seconds. Stopping the server."
                    )
                    server_manager.inactivity_time = 0
                    # Optionally send a message to a Discord channel
                    channel = discord.utils.get(
                        bot.get_all_channels(), name==CHANNEL_NAME
                    )
                    if channel:
                        await channel.send(
                            f"No players online for {INACTIVITY_LIMIT} seconds. Stopping the server."
                        )
                    # Stop the log monitoring thread
                    server_manager.stop_log_monitoring_thread()
        else:
            server_manager.inactivity_time = 0
    except docker.errors.NotFound:
        server_manager.inactivity_time = 0  # Reset timer if container doesn't exist
    except Exception as e:
        logging.error(f"Error in monitor_inactivity: {e}", exc_info=True)


@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user.name}")
    # Start the inactivity monitor
    monitor_inactivity.start()
    # Start the log monitoring thread
    server_manager.start_log_monitoring_thread()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(
            f"Unknown command: {ctx.message.content}. Use `!help` to see available commands."
        )
    else:
        logging.error(f"Unhandled exception: {error}", exc_info=True)
        await ctx.send(f"An error occurred: {error}")


bot.run(TOKEN)
