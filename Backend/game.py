import pygame
import socket
import json
import threading
import time
import sys
from pygame.locals import *

# Game Constants
CANVAS_SIZE = 700
PLAYER_SIZE = 30
OBJECT_SIZE = 20
POWERUP_SIZE = 15
RED_STAR_SIZE = 25  # Size of the special red star
GAME_DURATION = 120
BASE_SPEED = 5
MAX_PLAYERS = 4
RED_STAR_CLICKS_REQUIRED = 5  # Clicks required to collect the red star

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (80, 80, 80)
DARK_GRAY = (40, 40, 40)
YELLOW = (255, 215, 0)
BLUE_ICE = (140, 190, 230)
YELLOW_SPEED = (255, 255, 0)
BLUE_SLOW = (30, 144, 255)
PURPLE = (75, 0, 130)
LIGHT_PURPLE = (100, 50, 150)
RED = (255, 0, 0)
BRIGHT_RED = (255, 50, 50)

COLOR_MAP = {
    "red": (255, 0, 0),
    "blue": (0, 0, 255),
    "green": (0, 255, 0),
    "purple": (128, 0, 128),
}

SERVER_HOST = "localhost"
SERVER_PORT = 5001

PLAYER_CONTROLS = [
    {"up": K_UP, "down": K_DOWN, "left": K_LEFT, "right": K_RIGHT, "name": "Arrow Keys"},
    {"up": K_w, "down": K_s, "left": K_a, "right": K_d, "name": "WASD"},
    {"up": K_i, "down": K_k, "left": K_j, "right": K_l, "name": "IJKL"},
    {"up": K_t, "down": K_g, "left": K_f, "right": K_h, "name": "TFGH"}
]

# Initialize the mixer
pygame.mixer.init()
# Load the music
pygame.mixer.music.load("BG_Music.mp3")
# Set the volume
pygame.mixer.music.set_volume(0.7)


class GameClient:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((CANVAS_SIZE, CANVAS_SIZE + 100))
        pygame.display.set_caption("Multiplayer Game")
        self.clock = pygame.time.Clock()

        self.font_large = pygame.font.SysFont('Arial', 24)
        self.font_medium = pygame.font.SysFont('Arial', 20)
        self.font_small = pygame.font.SysFont('Arial', 16)

        # Initialize game state with default values
        self.game_state = {
            "players": [],
            "sharedObject": {"x": CANVAS_SIZE / 2 - OBJECT_SIZE / 2, "y": CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
                             "isHeld": False, "holderId": None},
            "obstacles": [],
            "powerups": [],
            "timeRemaining": GAME_DURATION,
            "gameStarted": False,
            "winner": None,
            "redStar": {
                "active": False,
                "x": 0,
                "y": 0,
                "clicksRequired": RED_STAR_CLICKS_REQUIRED,
                "clicksByPlayer": {},
                "expiresAt": 0
            }
        }
        self.player_id = None
        self.connected = False
        self.connection_error = None
        self.game_ended = False

        self.socket = None
        self.receive_thread = None
        self.running = True

        self.star_icon = self.create_star_icon()
        self.speed_icon = self.create_speed_icon()
        self.slow_icon = self.create_slow_icon()
        self.red_star_icon = self.create_red_star_icon()

        self.connect_to_server()

    def create_star_icon(self):
        icon = pygame.Surface((OBJECT_SIZE, OBJECT_SIZE), pygame.SRCALPHA)
        pygame.draw.polygon(icon, YELLOW, [
            (OBJECT_SIZE / 2, 0), (OBJECT_SIZE * 0.65, OBJECT_SIZE * 0.35), (OBJECT_SIZE, OBJECT_SIZE * 0.4),
            (OBJECT_SIZE * 0.75, OBJECT_SIZE * 0.65), (OBJECT_SIZE * 0.8, OBJECT_SIZE),
            (OBJECT_SIZE / 2, OBJECT_SIZE * 0.85), (OBJECT_SIZE * 0.2, OBJECT_SIZE),
            (OBJECT_SIZE * 0.25, OBJECT_SIZE * 0.65), (0, OBJECT_SIZE * 0.4), (OBJECT_SIZE * 0.35, OBJECT_SIZE * 0.35)
        ])
        return icon

    def create_red_star_icon(self):
        icon = pygame.Surface((RED_STAR_SIZE, RED_STAR_SIZE), pygame.SRCALPHA)
        pygame.draw.polygon(icon, RED, [
            (RED_STAR_SIZE / 2, 0), (RED_STAR_SIZE * 0.65, RED_STAR_SIZE * 0.35), (RED_STAR_SIZE, RED_STAR_SIZE * 0.4),
            (RED_STAR_SIZE * 0.75, RED_STAR_SIZE * 0.65), (RED_STAR_SIZE * 0.8, RED_STAR_SIZE),
            (RED_STAR_SIZE / 2, RED_STAR_SIZE * 0.85), (RED_STAR_SIZE * 0.2, RED_STAR_SIZE),
            (RED_STAR_SIZE * 0.25, RED_STAR_SIZE * 0.65), (0, RED_STAR_SIZE * 0.4),
            (RED_STAR_SIZE * 0.35, RED_STAR_SIZE * 0.35)
        ])
        # Add a glowing effect (pulsating outline)
        pygame.draw.polygon(icon, BRIGHT_RED, [
            (RED_STAR_SIZE / 2, 0), (RED_STAR_SIZE * 0.65, RED_STAR_SIZE * 0.35), (RED_STAR_SIZE, RED_STAR_SIZE * 0.4),
            (RED_STAR_SIZE * 0.75, RED_STAR_SIZE * 0.65), (RED_STAR_SIZE * 0.8, RED_STAR_SIZE),
            (RED_STAR_SIZE / 2, RED_STAR_SIZE * 0.85), (RED_STAR_SIZE * 0.2, RED_STAR_SIZE),
            (RED_STAR_SIZE * 0.25, RED_STAR_SIZE * 0.65), (0, RED_STAR_SIZE * 0.4),
            (RED_STAR_SIZE * 0.35, RED_STAR_SIZE * 0.35)
        ], 2)
        return icon

    def create_speed_icon(self):
        icon = pygame.Surface((POWERUP_SIZE, POWERUP_SIZE), pygame.SRCALPHA)
        pygame.draw.polygon(icon, YELLOW_SPEED, [
            (POWERUP_SIZE / 2, 0), (POWERUP_SIZE * 0.25, POWERUP_SIZE * 0.5), (POWERUP_SIZE * 0.6, POWERUP_SIZE * 0.5),
            (POWERUP_SIZE * 0.4, POWERUP_SIZE), (POWERUP_SIZE * 0.75, POWERUP_SIZE * 0.5),
            (POWERUP_SIZE * 0.4, POWERUP_SIZE * 0.5), (POWERUP_SIZE * 0.6, 0)
        ])
        return icon

    def create_slow_icon(self):
        icon = pygame.Surface((POWERUP_SIZE, POWERUP_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(icon, BLUE_SLOW, (POWERUP_SIZE // 2, POWERUP_SIZE // 2), POWERUP_SIZE // 2)
        pygame.draw.line(icon, WHITE, (POWERUP_SIZE // 2, 2), (POWERUP_SIZE // 2, POWERUP_SIZE - 2), 2)
        pygame.draw.line(icon, WHITE, (2, POWERUP_SIZE // 2), (POWERUP_SIZE - 2, POWERUP_SIZE // 2), 2)
        pygame.draw.line(icon, WHITE, (POWERUP_SIZE * 0.25, POWERUP_SIZE * 0.25),
                         (POWERUP_SIZE * 0.75, POWERUP_SIZE * 0.75), 2)
        pygame.draw.line(icon, WHITE, (POWERUP_SIZE * 0.25, POWERUP_SIZE * 0.75),
                         (POWERUP_SIZE * 0.75, POWERUP_SIZE * 0.25), 2)
        return icon

    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((SERVER_HOST, SERVER_PORT))
            self.connected = True
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
        except Exception as e:
            self.connection_error = f"Failed to connect: {e}"
            print(self.connection_error)
            self.connected = False

    def receive_messages(self):
        # Continously recieve messages while client is connected
        try:
        
            while self.running:
                # First, recieve the 4-byte message header
                header = self.recvall(4)
                # If header is None, the connection is closed
                if not header:
                    break
                # Convert the header to integer to get the message length
                message_length = int.from_bytes(header, byteorder='big')
                # Recieve the message data
                data = self.recvall(message_length)
                if not data:
                    break
                # Decode the data and parse the JSON message
                message = json.loads(data.decode('utf-8'))
                # Handle the server message
                self.handle_server_message(message)
        except Exception as e:
            self.connected = False
            print(f"Connection lost: {e}")
        finally:
            if self.socket:
                self.socket.close()
            self.socket = None

    def recvall(self, n):
        data = b''
        while len(data) < n:
            packet = self.socket.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    # Handle messages from the server
    def handle_server_message(self, message):
        # Get the type of message
        msg_type = message.get("type")
        if msg_type == "connection_accepted":
            # Connection accepted, get player ID and game state
            self.player_id = message.get("playerId")
            new_game_state = message.get("gameState")
            # Update the game state if provided
            if new_game_state:
                self.game_state.update(new_game_state)
            print(f"Connected as Player {self.player_id}")
        # If connection is rejected, set the error message
        elif msg_type == "connection_rejected":
            self.connection_error = message.get("message")
            self.connected = False
        # If the game state is updated, update the local game state
        elif msg_type == "game_state_update":
            # Update the game state with the new data
            new_game_state = message.get("gameState")
            if new_game_state:
                
                self.game_state.update(new_game_state)
                # Check if the game just ended
                if not self.game_state.get("gameStarted", False) and self.game_state.get("winner") is not None:
                    self.game_ended = True
            print(
                f"Received game state update for Player {self.player_id}: gameStarted={self.game_state.get('gameStarted', False)}")
            # If the game is over, set the game_ended flag
            for player in self.game_state.get("players", []):
                if player["id"] == self.player_id:
                    print(f"Player {self.player_id} position: ({player['x']}, {player['y']})")

    def send_message(self, message):
        try:
            if not self.connected or not self.socket:
                return
            data = json.dumps(message).encode('utf-8')
            length = len(data).to_bytes(4, byteorder='big')
            self.socket.sendall(length + data)
            print(f"Sent message: {message}")
        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False

    def move_player(self, direction):
        if not self.connected or not self.player_id or not self.game_state or not self.game_state.get("gameStarted"):
            print(
                f"Cannot move: connected={self.connected}, player_id={self.player_id}, game_started={self.game_state.get('gameStarted') if self.game_state else False}")
            return
        self.send_message({"type": "move", "direction": direction, "playerId": self.player_id})

    def click_red_star(self):
        if not self.connected or not self.player_id or not self.game_state or not self.game_state.get("gameStarted"):
            return
        self.send_message({"type": "click_red_star", "playerId": self.player_id})

    def start_game(self):
        if not self.connected or not self.is_player_one():
            return
        self.game_ended = False
        self.send_message({"type": "start_game"})

    # In the GameClient class, update the handle_input method
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                # Start game button in lobby
                if self.game_state and not self.game_state.get(
                        "gameStarted") and not self.game_ended and self.is_player_one():
                    start_button_rect = pygame.Rect(CANVAS_SIZE // 2 - 80, CANVAS_SIZE + 50, 160, 40)
                    if start_button_rect.collidepoint(mouse_pos):
                        self.start_game()

                # Check if the red star was clicked
                if self.game_state and self.game_state.get("gameStarted") and self.player_id is not None:
                    red_star = self.game_state.get("redStar", {})
                    if red_star.get("active", False):
                        # Get the player object
                        player = next((p for p in self.game_state.get("players", []) if p["id"] == self.player_id),
                                      None)
                        if player:
                            # Check if mouse is over red star
                            red_star_rect = pygame.Rect(red_star["x"], red_star["y"], RED_STAR_SIZE, RED_STAR_SIZE)
                            if red_star_rect.collidepoint(mouse_pos):
                                # Send the click to the server - removed the player collision check
                                self.click_red_star()
                                print(f"Player {self.player_id} clicked red star!")

        if self.game_state and self.game_state.get("gameStarted") and self.player_id is not None:
            keys = pygame.key.get_pressed()
            control_idx = self.player_id - 1 if self.player_id - 1 < len(PLAYER_CONTROLS) else 0
            controls = PLAYER_CONTROLS[control_idx]
            if keys[controls["up"]]:
                self.move_player("up")
            if keys[controls["down"]]:
                self.move_player("down")
            if keys[controls["left"]]:
                self.move_player("left")
            if keys[controls["right"]]:
                self.move_player("right")


    def is_player_one(self):
        return self.player_id == 1

    def render_connecting_screen(self):
        self.screen.fill(DARK_GRAY)
        if self.connection_error:
            text = self.font_large.render("Connection Error", True, (255, 0, 0))
            self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, CANVAS_SIZE // 2 - 40))
            text = self.font_medium.render(self.connection_error, True, WHITE)
            self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, CANVAS_SIZE // 2))
        else:
            text = self.font_large.render("Connecting to server...", True, WHITE)
            self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, CANVAS_SIZE // 2))

    def render_lobby_screen(self):
        self.screen.fill(DARK_GRAY)
        text = self.font_large.render("Game Lobby", True, WHITE)
        self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, 50))
        text = self.font_medium.render(f"Your ID: {self.player_id}", True, WHITE)
        self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, 80))

        text = self.font_medium.render("Connected Players:", True, WHITE)
        self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, 120))
        y_pos = 160
        for player in self.game_state.get("players", []):
            player_color = COLOR_MAP.get(player.get("color", "red"), (255, 0, 0))
            text = self.font_medium.render(f"Player {player['id']}{' (You)' if player['id'] == self.player_id else ''}",
                                           True, player_color)
            self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, y_pos))
            y_pos += 30

        # Game instructions
        y_pos += 30
        instructions_text = self.font_medium.render("Game Instructions:", True, WHITE)
        self.screen.blit(instructions_text, (CANVAS_SIZE // 2 - instructions_text.get_width() // 2, y_pos))

        y_pos += 30
        controls_text = self.font_small.render("Use your controls to move and collect the yellow star.", True, WHITE)
        self.screen.blit(controls_text, (CANVAS_SIZE // 2 - controls_text.get_width() // 2, y_pos))

        y_pos += 20
        red_star_text = self.font_small.render("Click the special RED star 5 times to get 5 bonus points!", True, RED)
        self.screen.blit(red_star_text, (CANVAS_SIZE // 2 - red_star_text.get_width() // 2, y_pos))

        if self.is_player_one():
            button_rect = pygame.Rect(CANVAS_SIZE // 2 - 80, CANVAS_SIZE + 50, 160, 40)
            pygame.draw.rect(self.screen, PURPLE, button_rect)
            pygame.draw.rect(self.screen, LIGHT_PURPLE, button_rect, 2)
            start_text = self.font_medium.render("Start Game", True, WHITE)
            self.screen.blit(start_text, (
                button_rect.centerx - start_text.get_width() // 2, button_rect.centery - start_text.get_height() // 2))
        else:
            wait_text = self.font_medium.render("Waiting for Player 1...", True, WHITE)
            self.screen.blit(wait_text, (CANVAS_SIZE // 2 - wait_text.get_width() // 2, CANVAS_SIZE + 60))

    def render_game_over_screen(self):
        self.screen.fill(DARK_GRAY)

        # Display winner
        winner = self.game_state.get("winner")
        winner_player = next((p for p in self.game_state.get("players", []) if p["id"] == winner), None)

        # Game over title
        text = self.font_large.render("GAME OVER", True, WHITE)
        self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, CANVAS_SIZE // 4))

        # Winner information
        if winner_player:
            winner_color = COLOR_MAP.get(winner_player.get("color", "red"), (255, 0, 0))
            winner_text = self.font_large.render(f"Player {winner} Wins!", True, winner_color)
            you_text = ""
            if winner == self.player_id:
                you_text = self.font_large.render("Congratulations!", True, WHITE)
            else:
                you_text = self.font_large.render("Better luck next time!", True, WHITE)

            self.screen.blit(winner_text, (CANVAS_SIZE // 2 - winner_text.get_width() // 2, CANVAS_SIZE // 3))
            self.screen.blit(you_text, (CANVAS_SIZE // 2 - you_text.get_width() // 2, CANVAS_SIZE // 3 + 40))

        # Display final scores
        text = self.font_medium.render("Final Scores:", True, WHITE)
        self.screen.blit(text, (CANVAS_SIZE // 2 - text.get_width() // 2, CANVAS_SIZE // 2))

        y_pos = CANVAS_SIZE // 2 + 30
        for player in sorted(self.game_state.get("players", []), key=lambda p: p.get("score", 0), reverse=True):
            player_color = COLOR_MAP.get(player.get("color", "red"), (255, 0, 0))
            score_text = self.font_medium.render(
                f"Player {player['id']}: {player['score']} points{' (You)' if player['id'] == self.player_id else ''}",
                True,
                player_color
            )
            self.screen.blit(score_text, (CANVAS_SIZE // 2 - score_text.get_width() // 2, y_pos))
            y_pos += 30

        # Informational text for all players
        info_text = self.font_medium.render("Game session ended", True, WHITE)
        self.screen.blit(info_text, (CANVAS_SIZE // 2 - info_text.get_width() // 2, CANVAS_SIZE // 2 + 90))

    def render_game(self):
        self.screen.fill(DARK_GRAY)
        pygame.draw.rect(self.screen, GRAY, (0, 0, CANVAS_SIZE, CANVAS_SIZE))

        for obstacle in self.game_state.get("obstacles", []):
            pygame.draw.rect(self.screen, BLUE_ICE, (obstacle["x"], obstacle["y"], obstacle["size"], obstacle["size"]))

        for powerup in self.game_state.get("powerups", []):
            if powerup.get("active", False):
                if powerup["type"] == "speed":
                    self.screen.blit(self.speed_icon, (powerup["x"], powerup["y"]))
                elif powerup["type"] == "slow":
                    self.screen.blit(self.slow_icon, (powerup["x"], powerup["y"]))

        shared_obj = self.game_state.get("sharedObject", {})
        self.screen.blit(self.star_icon, (shared_obj.get("x", 0), shared_obj.get("y", 0)))

        # Render red star if active
        red_star = self.game_state.get("redStar", {})
        if red_star.get("active", False):
            self.screen.blit(self.red_star_icon, (red_star.get("x", 0), red_star.get("y", 0)))

            # Draw progress indicator for the current player
            current_player_clicks = red_star.get("clicksByPlayer", {}).get(str(self.player_id), 0)
            if current_player_clicks > 0:
                progress_text = self.font_small.render(f"{current_player_clicks}/{RED_STAR_CLICKS_REQUIRED}", True,
                                                       WHITE)
                self.screen.blit(progress_text, (red_star.get("x", 0), red_star.get("y", 0) - 20))

        for player in self.game_state.get("players", []):
            player_color = COLOR_MAP.get(player.get("color", "red"), (255, 0, 0))
            player_rect = pygame.Rect(player["x"], player["y"], PLAYER_SIZE, PLAYER_SIZE)
            pygame.draw.rect(self.screen, player_color, player_rect)
            if player["id"] == self.player_id:
                pygame.draw.rect(self.screen, WHITE, player_rect, 2)

        pygame.draw.rect(self.screen, DARK_GRAY, (0, CANVAS_SIZE, CANVAS_SIZE, 100))
        time_text = self.font_large.render(f"Time: {self.game_state.get('timeRemaining', 0)}s", True, WHITE)
        self.screen.blit(time_text, (20, CANVAS_SIZE + 10))

        score_x = 20
        for player in self.game_state.get("players", []):
            player_color = COLOR_MAP.get(player.get("color", "red"), (255, 0, 0))
            score_text = self.font_medium.render(
                f"P{player['id']}: {player['score']}{' (You)' if player['id'] == self.player_id else ''}", True,
                player_color
            )
            self.screen.blit(score_text, (score_x, CANVAS_SIZE + 40))
            score_x += 150

        # Display red star status if active
        if red_star.get("active", False):
            time_left = max(0, red_star.get("expiresAt", 0) - time.time())
            red_star_text = self.font_medium.render(f"RED STAR! {time_left:.1f}s", True, RED)
            self.screen.blit(red_star_text, (CANVAS_SIZE - 150, CANVAS_SIZE + 40))

    def run(self):
        # Start the music
        #pygame.mixer.music.play(-1)  # -1 means loop indefinitely

        while self.running:
            self.handle_input()
            if not self.connected:
                self.render_connecting_screen()
            elif self.game_ended:
                self.render_game_over_screen()
            elif not self.game_state or not self.game_state.get("gameStarted"):
                self.render_lobby_screen()
            else:
                self.render_game()
            pygame.display.flip()
            self.clock.tick(60)

    def cleanup(self):
        self.running = False
        if self.socket:
            self.socket.close()
        pygame.mixer.music.stop()  # Stop music before quitting
        pygame.quit()


if __name__ == "__main__":
    client = GameClient()
    try:
        client.run()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.cleanup()
