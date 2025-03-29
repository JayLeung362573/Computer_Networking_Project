import asyncio
import json
import websockets
import random
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import time

# Constants
CANVAS_SIZE = 550
PLAYER_SIZE = 25
OBJECT_SIZE = 30
POWERUP_SIZE = 25
GAME_DURATION = 60
BASE_SPEED = 15
SPEED_BOOST = 10
SPEED_PENALTY = -30
NUM_OBSTACLES = 18
NUM_POWERUPS = 4

@dataclass
class Player:
    id: int
    x: float
    y: float
    speed: float
    score: int
    color: str
    hasObject: bool
    powerups: Dict[str, float]

@dataclass
class SharedObject:
    x: float
    y: float
    isHeld: bool
    holderId: Optional[int]

@dataclass
class Obstacle:
    x: float
    y: float
    size: float
    type: str

@dataclass
class Powerup:
    x: float
    y: float
    type: str
    active: bool

@dataclass
class GameState:
    players: Dict[int, Player]
    shared_object: SharedObject
    obstacles: List[Obstacle]
    powerups: List[Powerup]
    time_remaining: int
    game_started: bool
    winner: Optional[int]

class GameServer:
    def __init__(self):
        self.connections: Set[websockets.WebSocketServerProtocol] = set()
        self.game_state: Optional[GameState] = None
        self.game_task: Optional[asyncio.Task] = None
        self.player_counter = 0  # Counter for assigning unique player IDs
        self.player_colors = ['red', 'purple', 'blue', 'green']  # Available colors for players
        self.player_websockets: Dict[int, websockets.WebSocketServerProtocol] = {}  # Map player IDs to their websockets
        self.available_ids = set(range(1, 5))  # Available player IDs (1-4)

    def _generate_obstacles(self) -> List[Obstacle]:
        obstacles = []
        while len(obstacles) < NUM_OBSTACLES:
            new_obstacle = Obstacle(
                x=random.uniform(0, CANVAS_SIZE - PLAYER_SIZE * 4),
                y=random.uniform(0, CANVAS_SIZE - PLAYER_SIZE * 4),
                size=PLAYER_SIZE * 2,
                type='ice'
            )
            
            # Check for overlaps with existing obstacles
            is_overlapping = any(
                abs(obs.x - new_obstacle.x) < PLAYER_SIZE * 2.5 and
                abs(obs.y - new_obstacle.y) < PLAYER_SIZE * 2.5
                for obs in obstacles
            )
            
            if not is_overlapping:
                obstacles.append(new_obstacle)
        
        return obstacles

    def _generate_powerups(self) -> List[Powerup]:
        powerups = []
        while len(powerups) < NUM_POWERUPS:
            new_powerup = Powerup(
                x=random.uniform(0, CANVAS_SIZE - POWERUP_SIZE),
                y=random.uniform(0, CANVAS_SIZE - POWERUP_SIZE),
                type=random.choice(['speed', 'slow']),
                active=True
            )
            
            # Check for overlaps with existing powerups
            is_overlapping = any(
                abs(p.x - new_powerup.x) < POWERUP_SIZE * 2 and
                abs(p.y - new_powerup.y) < POWERUP_SIZE * 2
                for p in powerups
            )
            
            if not is_overlapping:
                powerups.append(new_powerup)
        
        return powerups

    def _initialize_game_state(self) -> GameState:
        # Generate obstacles and powerups
        obstacles = self._generate_obstacles()
        powerups = self._generate_powerups()
        
        # Create initial players
        players = {}
        for player_id in self.player_websockets.keys():
            # Assign positions based on player ID
            if player_id == 1:
                x, y = 10, 10
            elif player_id == 2:
                x, y = CANVAS_SIZE - PLAYER_SIZE - 10, CANVAS_SIZE - PLAYER_SIZE - 10
            elif player_id == 3:
                x, y = 10, CANVAS_SIZE - PLAYER_SIZE - 10
            else:  # player_id == 4
                x, y = CANVAS_SIZE - PLAYER_SIZE - 10, 10
            
            players[player_id] = Player(
                id=player_id,
                x=x,
                y=y,
                speed=BASE_SPEED,
                score=0,
                color=self.player_colors[player_id - 1],
                hasObject=False,
                powerups={'speedBoost': 0, 'speedPenalty': 0}
            )
        
        game_state = GameState(
            players=players,
            shared_object=SharedObject(
                x=CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
                y=CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
                isHeld=False,
                holderId=None
            ),
            obstacles=obstacles,
            powerups=powerups,
            time_remaining=GAME_DURATION,
            game_started=False,
            winner=None
        )
        print("Initialized game state:", asdict(game_state))  # Debug log
        return game_state

    async def _start_game(self):
        if not self.game_state:
            self.game_state = self._initialize_game_state()
        
        # Reset game state
        self.game_state = self._initialize_game_state()
        self.game_state.game_started = True
        
        # First send game_start message to all players
        game_state_dict = asdict(self.game_state)
        print("Broadcasting game start with state:", game_state_dict)  # Debug log
        await self._broadcast({
            'type': 'game_start',
            'game_state': game_state_dict
        })
        
        # Start game loop
        self.game_task = asyncio.create_task(self._game_loop())

    async def _game_loop(self):
        while self.game_state and self.game_state.time_remaining > 0:
            await asyncio.sleep(1)
            self.game_state.time_remaining -= 1
            
            # Update powerup timers
            current_time = time.time() * 1000
            for player in self.game_state.players.values():
                player.powerups['speedBoost'] = max(0, player.powerups['speedBoost'] - 1000)
                player.powerups['speedPenalty'] = max(0, player.powerups['speedPenalty'] - 1000)
            
            # Broadcast updated game state
            await self._broadcast({
                'type': 'game_state_update',
                'game_state': asdict(self.game_state)
            })
        
        # Game ended
        if self.game_state:
            # Determine winner
            winner = max(self.game_state.players.items(), key=lambda x: x[1].score)[0]
            self.game_state.winner = winner
            self.game_state.game_started = False
            
            # Broadcast game end
            await self._broadcast({
                'type': 'game_end',
                'winner': winner,
                'game_state': asdict(self.game_state)
            })

    async def _handle_player_connection(self, websocket: websockets.WebSocketServerProtocol):
        # Assign the lowest available player ID
        if not self.available_ids:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Game is full'
            }))
            return

        player_id = min(self.available_ids)
        self.available_ids.remove(player_id)
        
        # Store the connection
        self.connections.add(websocket)
        self.player_websockets[player_id] = websocket
        
        try:
            # Send initial player ID to the client
            await websocket.send(json.dumps({
                'type': 'init',
                'player_id': player_id
            }))

            # If there's an active game, send the current game state
            if self.game_state and self.game_state.game_started:
                # Create a new player for the connecting client
                if player_id not in self.game_state.players:
                    # Assign position based on player ID
                    if player_id == 1:
                        x, y = 10, 10
                    elif player_id == 2:
                        x, y = CANVAS_SIZE - PLAYER_SIZE - 10, CANVAS_SIZE - PLAYER_SIZE - 10
                    elif player_id == 3:
                        x, y = 10, CANVAS_SIZE - PLAYER_SIZE - 10
                    else:  # player_id == 4
                        x, y = CANVAS_SIZE - PLAYER_SIZE - 10, 10

                    self.game_state.players[player_id] = Player(
                        id=player_id,
                        x=x,
                        y=y,
                        speed=BASE_SPEED,
                        score=0,
                        color=self.player_colors[player_id - 1],
                        hasObject=False,
                        powerups={'speedBoost': 0, 'speedPenalty': 0}
                    )

                # Send the current game state to the new player
                await websocket.send(json.dumps({
                    'type': 'game_state_update',
                    'game_state': asdict(self.game_state)
                }))
            
            # Handle messages from this player
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            print(f"Player {player_id} disconnected")
        finally:
            # Clean up when player disconnects
            self.connections.remove(websocket)
            if player_id in self.player_websockets:
                del self.player_websockets[player_id]
                self.available_ids.add(player_id)  # Make the ID available again
            
            # If game is running, remove player from game state
            if self.game_state and player_id in self.game_state.players:
                del self.game_state.players[player_id]
                
                # If no players left, stop the game
                if not self.game_state.players:
                    if self.game_task:
                        self.game_task.cancel()
                    self.game_state = None
                else:
                    # Broadcast player disconnection
                    await self._broadcast({
                        'type': 'player_disconnected',
                        'player_id': player_id,
                        'game_state': asdict(self.game_state)
                    })

    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, message: str):
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'ready':
                # Find the player ID for this websocket
                player_id = next((pid for pid, ws in self.player_websockets.items() if ws == websocket), None)
                if player_id is None:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Player not found'
                    }))
                    return
                
                # Only allow player 1 to start the game
                if player_id != 1:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Only player 1 can start the game'
                    }))
                    return
                
                print(f"Player {player_id} requested to start the game")  # Debug log
                await self._start_game()
            
            elif message_type == 'move':
                if not self.game_state or not self.game_state.game_started:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Game not started'
                    }))
                    return
                
                player_id = data.get('player_id')
                dx = data.get('dx', 0)
                dy = data.get('dy', 0)
                
                if player_id not in self.game_state.players:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Player not found'
                    }))
                    return
                
                player = self.game_state.players[player_id]
                
                # Apply speed effects based on powerups
                current_time = time.time() * 1000
                speed = player.speed
                if player.powerups['speedBoost'] > current_time:
                    speed += SPEED_BOOST
                if player.powerups['speedPenalty'] > current_time:
                    speed = SPEED_PENALTY
                
                # Calculate new position
                new_x = player.x + dx * speed
                new_y = player.y + dy * speed
                
                # Boundary checks
                new_x = max(0, min(CANVAS_SIZE - PLAYER_SIZE, new_x))
                new_y = max(0, min(CANVAS_SIZE - PLAYER_SIZE, new_y))
                
                # Obstacle collision checks
                for obstacle in self.game_state.obstacles:
                    if (new_x < obstacle.x + obstacle.size and
                        new_x + PLAYER_SIZE > obstacle.x and
                        new_y < obstacle.y + obstacle.size and
                        new_y + PLAYER_SIZE > obstacle.y):
                        # Collision detected, revert to previous position
                        new_x = player.x
                        new_y = player.y
                
                # Player-to-Player collision checks
                for other_id, other_player in self.game_state.players.items():
                    if other_id != player_id:
                        if (new_x < other_player.x + PLAYER_SIZE and
                            new_x + PLAYER_SIZE > other_player.x and
                            new_y < other_player.y + PLAYER_SIZE and
                            new_y + PLAYER_SIZE > other_player.y):
                            # Collision detected, revert to previous position
                            new_x = player.x
                            new_y = player.y
                
                # Update player position
                player.x = new_x
                player.y = new_y
                
                # Check for powerup collection
                for powerup in self.game_state.powerups:
                    if powerup.active:
                        if (abs(new_x - powerup.x) < POWERUP_SIZE and 
                            abs(new_y - powerup.y) < POWERUP_SIZE):
                            powerup.active = False
                            if powerup.type == 'speed':
                                player.powerups['speedBoost'] = current_time + 8000  # 8 seconds speed boost
                            elif powerup.type == 'slow':
                                # Apply slow effect to other players
                                for other_id, other_player in self.game_state.players.items():
                                    if other_id != player_id:
                                        other_player.powerups['speedPenalty'] = current_time + 10000  # 10 seconds speed penalty
                
                # Check for shared object collection
                if not self.game_state.shared_object.isHeld:
                    if (abs(new_x - self.game_state.shared_object.x) < OBJECT_SIZE and 
                        abs(new_y - self.game_state.shared_object.y) < OBJECT_SIZE):
                        player.score += 1
                        # Reset shared object position
                        self.game_state.shared_object.x = random.randint(0, CANVAS_SIZE - OBJECT_SIZE)
                        self.game_state.shared_object.y = random.randint(0, CANVAS_SIZE - OBJECT_SIZE)
                
                # Broadcast updated game state
                await self._broadcast({
                    'type': 'game_state_update',
                    'game_state': asdict(self.game_state)
                })
            
            else:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
        
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON message'
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def _broadcast(self, message: dict):
        if not self.connections:
            return
        
        message_str = json.dumps(message)
        await asyncio.gather(
            *[connection.send(message_str) for connection in self.connections]
        )

async def main():
    game_server = GameServer()
    server = await websockets.serve(
        game_server._handle_player_connection,
        "localhost",
        8765
    )
    print("Game server started on ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())