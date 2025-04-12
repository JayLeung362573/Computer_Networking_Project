#!/usr/bin/env python3
import socket
import threading
import json
import time
import random
import math

# Game Constants
CANVAS_SIZE = 700
PLAYER_SIZE = 30
OBJECT_SIZE = 20
POWERUP_SIZE = 15
RED_STAR_SIZE = 25  # Size of the special red star
GAME_DURATION = 120
BASE_SPEED = 5
SPEED_BOOST = 3
SPEED_PENALTY = 2
NUM_OBSTACLES = 18
NUM_POWERUPS = 4
MAX_PLAYERS = 4
RED_STAR_POINTS = 5  # Points awarded for collecting the red star
RED_STAR_CLICKS_REQUIRED = 5  # Clicks required to collect the red star
RED_STAR_DURATION = 5  # Duration in seconds that the red star stays on screen
RED_STAR_MIN_INTERVAL = 15  # Minimum seconds between red star appearances
RED_STAR_MAX_INTERVAL = 30  # Maximum seconds between red star appearances

STARTING_POSITIONS = [
    {"x": 10, "y": 10, "color": "red"},
    {"x": CANVAS_SIZE - PLAYER_SIZE - 10, "y": CANVAS_SIZE - PLAYER_SIZE - 10, "color": "purple"},
    {"x": 10, "y": CANVAS_SIZE - PLAYER_SIZE - 10, "color": "blue"},
    {"x": CANVAS_SIZE - PLAYER_SIZE - 10, "y": 10, "color": "green"}
]


class GameServer:
    def __init__(self, host='0.0.0.0', port=5001):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # client_id: (socket, address, player_id)
        self.next_player_id = 1

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
                "clicksByPlayer": {},  # Track clicks by each player
                "expiresAt": 0  # Time when the red star will disappear
            }
        }
        self.game_timer = None
        self.red_star_timer = None

    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"Server started on {self.host}:{self.port}")
            game_thread = threading.Thread(target=self.game_loop)
            game_thread.daemon = True
            game_thread.start()
            self.accept_connections()
        except Exception as e:
            print(f"Error starting server: {e}")
            if self.server_socket:
                self.server_socket.close()

    def shutdown_server(self):
        print("Shutting down server...")
        if self.game_timer:
            self.game_timer.cancel()
        if self.red_star_timer:
            self.red_star_timer.cancel()
        for _, (client_socket, _, _) in list(self.clients.items()):
            try:
                client_socket.close()
            except:
                pass
        self.clients.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

    def accept_connections(self):
        print("Waiting for players...")
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                print(f"New connection from {address}")
                if len(self.game_state["players"]) >= MAX_PLAYERS:
                    self.send_message_to_client(client_socket,
                                                {"type": "connection_rejected", "message": "Game is full"})
                    client_socket.close()
                    continue
                client_id = len(self.clients) + 1
                player_id = self.next_player_id
                self.next_player_id += 1
                position = STARTING_POSITIONS[player_id - 1]
                new_player = {"id": player_id, "x": position["x"], "y": position["y"], "speed": BASE_SPEED, "score": 0,
                              "color": position["color"], "hasObject": False,
                              "powerups": {"speedBoost": 0, "speedPenalty": 0}}
                self.game_state["players"].append(new_player)
                self.clients[client_id] = (client_socket, address, player_id)
                self.send_message_to_client(client_socket, {"type": "connection_accepted", "playerId": player_id,
                                                            "gameState": self.game_state})
                if player_id == 1 and not self.game_state["gameStarted"]:
                    self.initialize_game_map()
                self.broadcast_game_state()
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_id))
                client_thread.daemon = True
                client_thread.start()
        except Exception as e:
            print(f"Error accepting connections: {e}")
        finally:
            self.shutdown_server()

    def handle_client(self, client_socket, client_id):
        try:
            while True:
                header = self.recvall(client_socket, 4)
                if not header:
                    break
                message_length = int.from_bytes(header, byteorder='big')
                data = self.recvall(client_socket, message_length)
                if not data:
                    break
                message = json.loads(data.decode('utf-8'))
                print(f"Received from client {client_id}: {message}")
                self.process_client_message(client_id, message)
        except Exception as e:
            print(f"Error with client {client_id}: {e}")
        finally:
            self.handle_client_disconnect(client_id)

    def recvall(self, sock, n):
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data


    def process_client_message(self, client_id, message):
        # Process the message from the client
        msg_type = message.get("type")
        # Get the player ID from the client
        player_id = self.clients[client_id][2]
        # Check if the player ID is valid
        if msg_type == "move":
            # Get the direction from the message
            direction = message.get("direction")
            # Check if the direction is valid
            received_player_id = message.get("playerId")
            # Check if the player ID matches
            if received_player_id == player_id:
                print(f"Processing move for Player {player_id}: {direction}")
                # Initialize the move
                self.move_player(player_id, direction)
            # Unauthorized move attempt
            else:
                print(f"Player {player_id} tried to move Player {received_player_id} - unauthorized")
        # Check if the message is to start the game
        elif msg_type == "start_game" and player_id == 1:
            print("Starting game by Player 1")
            self.start_game()
        # Check if the message is to click the red star
        elif msg_type == "click_red_star":
            received_player_id = message.get("playerId")
            if received_player_id == player_id:
                print(f"Player {player_id} clicked red star")
                self.handle_red_star_click(player_id)

    # In the GameServer class, update the handle_red_star_click method
    def handle_red_star_click(self, player_id):
        red_star = self.game_state["redStar"]
        if not red_star["active"] or time.time() > red_star["expiresAt"]:
            return

        # Find the player
        player = next((p for p in self.game_state["players"] if p["id"] == player_id), None)
        if not player:
            return

        # Check if player's position is within range of the red star (more lenient)
        # Calculate distance between player center and red star center
        # player_center_x = player["x"] + PLAYER_SIZE / 2
        # player_center_y = player["y"] + PLAYER_SIZE / 2
        # star_center_x = red_star["x"] + RED_STAR_SIZE / 2
        # star_center_y = red_star["y"] + RED_STAR_SIZE / 2

        # # Use a more generous interaction range - player can click from a distance
        # interaction_distance = PLAYER_SIZE + RED_STAR_SIZE * 5  # More lenient distance
        # distance = ((player_center_x - star_center_x) ** 2 + (player_center_y - star_center_y) ** 2) ** 0.5

        # if distance > interaction_distance:
        #     print(f"Player {player_id} clicked but is too far from red star")
        #     return

        # Store player ID as string to ensure consistent dictionary key type
        player_id_str = str(player_id)

        # Update clicks for this player
        if player_id_str not in red_star["clicksByPlayer"]:
            red_star["clicksByPlayer"][player_id_str] = 0
        red_star["clicksByPlayer"][player_id_str] += 1

        print(
            f"Player {player_id} clicked red star ({red_star['clicksByPlayer'][player_id_str]}/{RED_STAR_CLICKS_REQUIRED})")

        # Check if this player has clicked enough times
        if red_star["clicksByPlayer"][player_id_str] >= RED_STAR_CLICKS_REQUIRED:
            print(f"Player {player_id} collected red star! +{RED_STAR_POINTS} points")
            player["score"] += RED_STAR_POINTS
            red_star["active"] = False
            red_star["clicksByPlayer"] = {}
            if self.red_star_timer:
                self.red_star_timer.cancel()
            self.schedule_red_star()

        self.broadcast_game_state()


    def move_player(self, player_id, direction):
        print(f"[Server] move_player() called for Player {player_id} direction: {direction}")

        if not self.game_state["gameStarted"]:
            print("[Server] ❌ Move rejected: Game not started")
            return

        player = next((p for p in self.game_state["players"] if p["id"] == player_id), None)
        if not player:
            print(f"[Server] ❌ Player {player_id} not found")
            return

        dx, dy = 0, 0
        if direction == "up":
            dy = -1
        elif direction == "down":
            dy = 1
        elif direction == "left":
            dx = -1
        elif direction == "right":
            dx = 1
        else:
            print(f"[Server] ❌ Invalid direction: {direction}")
            return

        current_time = time.time() * 1000
        speed = player["speed"]
        if player["powerups"]["speedBoost"] > current_time:
            print(f"[Server] 🚀 Speed boost active for Player {player_id}")
            speed += SPEED_BOOST
        if player["powerups"]["speedPenalty"] > current_time:
            print(f"[Server] 🐢 Speed penalty active for Player {player_id}")
            speed = max(2, speed - SPEED_PENALTY)

        new_x = player["x"] + dx * speed
        new_y = player["y"] + dy * speed
        new_x = max(0, min(CANVAS_SIZE - PLAYER_SIZE, new_x))
        new_y = max(0, min(CANVAS_SIZE - PLAYER_SIZE, new_y))

        # Collision with obstacles
        for obstacle in self.game_state["obstacles"]:
            if self.check_collision(new_x, new_y, PLAYER_SIZE, obstacle["x"], obstacle["y"], obstacle["size"]):
                print(f"[Server] ⛔ Collision with obstacle — reverting position")
                new_x, new_y = player["x"], player["y"]
                break

        # Collision with other players
        for other in self.game_state["players"]:
            if other["id"] != player_id:
                if self.check_collision(new_x, new_y, PLAYER_SIZE, other["x"], other["y"], PLAYER_SIZE):
                    print(f"[Server] ⛔ Collision with another player — reverting position")
                    new_x, new_y = player["x"], player["y"]
                    break

        # Powerup collection
        for i, powerup in enumerate(self.game_state["powerups"]):
            if powerup["active"] and self.check_collision(new_x, new_y, PLAYER_SIZE, powerup["x"], powerup["y"],
                                                          POWERUP_SIZE):
                self.game_state["powerups"][i]["active"] = False
                if powerup["type"] == "speed":
                    print(f"[Server] ⚡ Player {player_id} collected speed powerup")
                    player["powerups"]["speedBoost"] = current_time + 8000
                elif powerup["type"] == "slow":
                    print(f"[Server] 🧊 Player {player_id} collected slow powerup")
                    player["powerups"]["speedPenalty"] = current_time + 10000

        # Shared object collection
        shared_obj = self.game_state["sharedObject"]
        if not shared_obj["isHeld"] and self.check_collision(new_x, new_y, PLAYER_SIZE, shared_obj["x"],
                                                             shared_obj["y"], OBJECT_SIZE):
            print(f"[Server] 🌟 Player {player_id} collected shared object")
            valid_position = False
            while not valid_position:
                new_obj_x = random.randint(0, CANVAS_SIZE - OBJECT_SIZE)
                new_obj_y = random.randint(0, CANVAS_SIZE - OBJECT_SIZE)
                valid_position = True
                for obstacle in self.game_state["obstacles"]:
                    if self.check_collision(new_obj_x, new_obj_y, OBJECT_SIZE, obstacle["x"], obstacle["y"],
                                            obstacle["size"]):
                        valid_position = False
                        break
                if valid_position:
                    for powerup in self.game_state["powerups"]:
                        if powerup["active"] and self.check_collision(new_obj_x, new_obj_y, OBJECT_SIZE,
                                                                      powerup["x"], powerup["y"], POWERUP_SIZE):
                            valid_position = False
                            break
            shared_obj["x"] = new_obj_x
            shared_obj["y"] = new_obj_y
            player["score"] += 1
            print(
                f"[Server] 🎯 New object location: ({new_obj_x}, {new_obj_y}) — Player {player_id} score: {player['score']}")

        old_x, old_y = player["x"], player["y"]
        player["x"] = new_x
        player["y"] = new_y
        if old_x != new_x or old_y != new_y:
            print(f"[Server] ✅ Player {player_id} moved from ({old_x}, {old_y}) → ({new_x}, {new_y})")
        else:
            print(f"[Server] ℹ️ Player {player_id} position unchanged")

        # Always broadcast the updated game state
        print(f"[Server] 📡 Broadcasting game state after move by Player {player_id}")
        self.broadcast_game_state()

    def check_collision(self, x1, y1, size1, x2, y2, size2):
        return (x1 < x2 + size2 and x1 + size1 > x2 and y1 < y2 + size2 and y1 + size1 > y2)

    def start_game(self):
        for player in self.game_state["players"]:
            for pos in STARTING_POSITIONS:
                if pos["color"] == player["color"]:
                    player["x"] = pos["x"]
                    player["y"] = pos["y"]
                    break
            player["score"] = 0
            player["powerups"]["speedBoost"] = 0
            player["powerups"]["speedPenalty"] = 0
        self.game_state["sharedObject"]["x"] = CANVAS_SIZE / 2 - OBJECT_SIZE / 2
        self.game_state["sharedObject"]["y"] = CANVAS_SIZE / 2 - OBJECT_SIZE / 2
        self.game_state["sharedObject"]["isHeld"] = False
        self.game_state["sharedObject"]["holderId"] = None
        self.game_state["obstacles"] = self.generate_obstacles()
        self.game_state["powerups"] = self.generate_powerups()
        self.game_state["timeRemaining"] = GAME_DURATION
        self.game_state["gameStarted"] = True
        self.game_state["winner"] = None
        self.game_state["redStar"]["active"] = False
        self.game_state["redStar"]["clicksByPlayer"] = {}

        print("Game started")
        self.broadcast_game_state()

        if self.game_timer:
            self.game_timer.cancel()
        self.game_timer = threading.Timer(1.0, self.update_game_timer)
        self.game_timer.daemon = True
        self.game_timer.start()

        # Schedule the first red star appearance
        self.schedule_red_star()

    def schedule_red_star(self):
        if not self.game_state["gameStarted"]:
            return

        interval = random.randint(RED_STAR_MIN_INTERVAL, RED_STAR_MAX_INTERVAL)
        print(f"[Server] Scheduling red star to appear in {interval} seconds")

        if self.red_star_timer:
            self.red_star_timer.cancel()

        self.red_star_timer = threading.Timer(interval, self.spawn_red_star)
        self.red_star_timer.daemon = True
        self.red_star_timer.start()

    def spawn_red_star(self):
        if not self.game_state["gameStarted"]:
            return

        print("[Server] 🔴 Spawning red star")

        valid_position = False
        while not valid_position:
            x = random.randint(0, CANVAS_SIZE - RED_STAR_SIZE)
            y = random.randint(0, CANVAS_SIZE - RED_STAR_SIZE)

            valid_position = True

            # Check collision with obstacles
            for obstacle in self.game_state["obstacles"]:
                if self.check_collision(x, y, RED_STAR_SIZE, obstacle["x"], obstacle["y"], obstacle["size"]):
                    valid_position = False
                    break

            # Check collision with powerups
            if valid_position:
                for powerup in self.game_state["powerups"]:
                    if powerup["active"] and self.check_collision(x, y, RED_STAR_SIZE,
                                                                  powerup["x"], powerup["y"], POWERUP_SIZE):
                        valid_position = False
                        break

            # Check collision with shared object
            if valid_position:
                shared_obj = self.game_state["sharedObject"]
                if self.check_collision(x, y, RED_STAR_SIZE, shared_obj["x"], shared_obj["y"], OBJECT_SIZE):
                    valid_position = False

        # Set red star properties
        self.game_state["redStar"]["active"] = True
        self.game_state["redStar"]["x"] = x
        self.game_state["redStar"]["y"] = y
        self.game_state["redStar"]["clicksByPlayer"] = {}
        self.game_state["redStar"]["expiresAt"] = time.time() + RED_STAR_DURATION

        # Broadcast the updated game state
        self.broadcast_game_state()

        # Schedule the red star to disappear
        disappear_timer = threading.Timer(RED_STAR_DURATION, self.remove_red_star)
        disappear_timer.daemon = True
        disappear_timer.start()

    def remove_red_star(self):
        if self.game_state["redStar"]["active"]:
            print("[Server] 🔴 Red star disappeared (timeout)")
            self.game_state["redStar"]["active"] = False
            self.game_state["redStar"]["clicksByPlayer"] = {}
            self.broadcast_game_state()

        # Schedule the next red star
        self.schedule_red_star()

    def update_game_timer(self):
        if not self.game_state["gameStarted"]:
            return
        self.game_state["timeRemaining"] -= 1
        current_time = time.time() * 1000
        for player in self.game_state["players"]:
            player["powerups"]["speedBoost"] = max(0, player["powerups"]["speedBoost"])
            player["powerups"]["speedPenalty"] = max(0, player["powerups"]["speedPenalty"])
        if self.game_state["timeRemaining"] <= 0:
            self.end_game()
        else:
            self.game_timer = threading.Timer(1.0, self.update_game_timer)
            self.game_timer.daemon = True
            self.game_timer.start()
            self.broadcast_game_state()

    def end_game(self):
        highest = -1
        winner_id = None
        for player in self.game_state["players"]:
            if player["score"] > highest:
                highest = player["score"]
                winner_id = player["id"]
        self.game_state["gameStarted"] = False
        self.game_state["winner"] = winner_id

        # Clear any active red star
        self.game_state["redStar"]["active"] = False
        if self.red_star_timer:
            self.red_star_timer.cancel()

        print(f"Game ended. Winner: Player {winner_id}")
        self.broadcast_game_state()

    def initialize_game_map(self):
        self.game_state["obstacles"] = self.generate_obstacles()
        self.game_state["powerups"] = self.generate_powerups()

    def generate_obstacles(self):
        obstacles = []
        shared_obj = self.game_state["sharedObject"]
        while len(obstacles) < NUM_OBSTACLES:
            new_obstacle = {"x": random.uniform(0, CANVAS_SIZE - PLAYER_SIZE * 4),
                            "y": random.uniform(0, CANVAS_SIZE - PLAYER_SIZE * 4), "size": PLAYER_SIZE * 2,
                            "type": "ice"}
            overlapping = False
            for obs in obstacles:
                if math.hypot(obs["x"] - new_obstacle["x"], obs["y"] - new_obstacle["y"]) < PLAYER_SIZE * 2.5:
                    overlapping = True
                    break
            if overlapping:
                continue
            for player in self.game_state["players"]:
                if math.hypot(player["x"] - new_obstacle["x"], player["y"] - new_obstacle["y"]) < PLAYER_SIZE * 4:
                    overlapping = True
                    break
            if overlapping:
                continue
            if math.hypot(shared_obj["x"] - new_obstacle["x"], shared_obj["y"] - new_obstacle["y"]) < OBJECT_SIZE * 3:
                continue
            obstacles.append(new_obstacle)
        return obstacles

    def generate_powerups(self):
        powerups = []
        obstacles = self.game_state["obstacles"]
        shared_obj = self.game_state["sharedObject"]
        for _ in range(NUM_POWERUPS // 2):
            while True:
                x = random.uniform(0, CANVAS_SIZE - POWERUP_SIZE)
                y = random.uniform(0, CANVAS_SIZE - POWERUP_SIZE)
                if not any(math.hypot(p["x"] - x, p["y"] - y) < 30 * 5 for p in powerups) and \
                        not any(self.check_collision(x, y, POWERUP_SIZE, obs["x"], obs["y"], obs["size"]) for obs in
                                obstacles) and \
                        math.hypot(shared_obj["x"] - x, shared_obj["y"] - y) >= OBJECT_SIZE * 5:
                    powerups.append({"x": x, "y": y, "type": "speed", "active": True})
                    break
        for _ in range(NUM_POWERUPS // 2):
            while True:
                x = random.uniform(0, CANVAS_SIZE - POWERUP_SIZE)
                y = random.uniform(0, CANVAS_SIZE - POWERUP_SIZE)
                if not any(math.hypot(p["x"] - x, p["y"] - y) < 30 * 5 for p in powerups) and \
                        not any(self.check_collision(x, y, POWERUP_SIZE, obs["x"], obs["y"], obs["size"]) for obs in
                                obstacles) and \
                        math.hypot(shared_obj["x"] - x, shared_obj["y"] - y) >= OBJECT_SIZE * 5:
                    powerups.append({"x": x, "y": y, "type": "slow", "active": True})
                    break
        return powerups

    def broadcast_game_state(self):
        # Make a deep copy to prevent mutation
        game_state_copy = json.loads(json.dumps(self.game_state))

        message = {"type": "game_state_update", "gameState": game_state_copy}
        for client_id, (client_socket, _, player_id) in list(self.clients.items()):
            try:
                self.send_message_to_client(client_socket, message)
                print(f"Broadcasted game state to Player {player_id}")
            except Exception as e:
                print(f"Error sending to client {client_id}: {e}")
                self.handle_client_disconnect(client_id)

    def send_message_to_client(self, client_socket, message):
        data = json.dumps(message).encode('utf-8')
        length = len(data).to_bytes(4, byteorder='big')
        client_socket.sendall(length + data)

    def handle_client_disconnect(self, client_id):
        if client_id in self.clients:
            client_socket, _, player_id = self.clients[client_id]
            try:
                client_socket.close()
            except:
                pass
            del self.clients[client_id]
            print(f"Client {client_id} (Player {player_id}) disconnected")

        self.game_state["players"] = [p for p in self.game_state["players"] if p["id"] != player_id]
        if not self.game_state["players"] and self.game_state["gameStarted"]:
            self.game_state["gameStarted"] = False
            if self.game_timer:
                self.game_timer.cancel()
                self.game_timer = None
            if self.red_star_timer:
                self.red_star_timer.cancel()
                self.red_star_timer = None
        self.broadcast_game_state()

    def game_loop(self):
        while True:
            if self.game_state["gameStarted"]:
                current_time = time.time() * 1000
                for player in self.game_state["players"]:
                    player["powerups"]["speedBoost"] = max(0, player["powerups"]["speedBoost"])
                    player["powerups"]["speedPenalty"] = max(0, player["powerups"]["speedPenalty"])

                # Check if red star has expired
                if self.game_state["redStar"]["active"] and time.time() > self.game_state["redStar"]["expiresAt"]:
                    self.remove_red_star()

            time.sleep(0.01)


if __name__ == "__main__":
    server = GameServer(host='0.0.0.0', port=5001)
    try:
        server.start_server()
    except KeyboardInterrupt:
        server.shutdown_server()