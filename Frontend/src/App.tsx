import React, { useEffect, useState, useCallback } from 'react';
import { Timer, Trophy, Star, Zap, SunSnow as Snow } from 'lucide-react';
import {
  Player, SharedObject, GameState, Obstacle, Powerup,
  CANVAS_SIZE, PLAYER_SIZE, OBJECT_SIZE, POWERUP_SIZE,
  GAME_DURATION, BASE_SPEED, SPEED_BOOST, SPEED_PENALTY,
} from './types';

const NUM_OBSTACLES = 18;
const NUM_POWERUPS = 4;

function generateObstacles(players: Player[], sharedObject: SharedObject): Obstacle[] {
  const type: 'ice' = 'ice';
  const obstacles: Obstacle[] = [];

  while (obstacles.length < NUM_OBSTACLES) {
    const newObstacle: Obstacle = {
      x: Math.random() * (CANVAS_SIZE - PLAYER_SIZE * 4),
      y: Math.random() * (CANVAS_SIZE - PLAYER_SIZE * 4),
      size: PLAYER_SIZE * 2,
      type: type
    };

    // Check for overlaps
    const isOverlapping = obstacles.some(obstacle => {
      const dx = obstacle.x - newObstacle.x;
      const dy = obstacle.y - newObstacle.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return distance < PLAYER_SIZE * 2.5; // Ensure they don't overlap
    })|| players.some(player => {
      const dx = player.x - newObstacle.x;
      const dy = player.y - newObstacle.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return distance < PLAYER_SIZE * 4; // Ensure no overlap with players
    })|| Math.sqrt((sharedObject.x - newObstacle.x) ** 2 + (sharedObject.y - newObstacle.y) ** 2) < OBJECT_SIZE*3;

    if (!isOverlapping) {
      obstacles.push(newObstacle);
    }
  }
  
  return obstacles;
}


function isOverlapping(x: number, y: number, size: number, obstacles:Obstacle[]): boolean {
  return obstacles.some(obstacle =>
    x < obstacle.x + obstacle.size &&
    x + size > obstacle.x &&
    y < obstacle.y + obstacle.size &&
    y + size > obstacle.y
  );
}
function isPowerupOvelapWithEachOther(x: number, y: number, powerups: Powerup[], sharedObject:SharedObject): boolean {
  // return Math.sqrt((sharedObject.x - x) ** 2 + (sharedObject.y - y) ** 2) < OBJECT_SIZE * 5;
  const isSharedObjectOverlap = Math.sqrt((sharedObject.x - x) ** 2 + (sharedObject.y - y) ** 2) < OBJECT_SIZE * 5;

  // Check for overlaps with each existing powerup
  const isPowerupOverlap = powerups.some((powerup) => {
    const distance = Math.sqrt((powerup.x - x) ** 2 + (powerup.y - y) ** 2);
    return distance < 30*5;
  });

  // If either overlap is true, return true
  return isSharedObjectOverlap || isPowerupOverlap;
}

function generatePowerups(obstacles: Obstacle[], players: Player[], sharedObject: SharedObject): Powerup[] {
  const types: ('speed' | 'slow')[] = ['speed', 'slow'];
  const powerups: Powerup[] = [];

  // Calculate the number of powerups to generate (must be an even number)
  const numSpeedAndSlow = Math.floor(NUM_POWERUPS / 2);

  // Generate 'speed' powerups
  while (powerups.filter(p => p.type === 'speed').length < numSpeedAndSlow) {
    const obstacle = obstacles[Math.floor(Math.random() * obstacles.length)];
    const x = Math.random() * (obstacle.x + obstacle.size);
    const y = Math.random() * (obstacle.y + obstacle.size);

    // Ensure powerups are not overlapping with players
    const isOverlappingWithPlayer = players.some(player => {
      const dx = player.x - x;
      const dy = player.y - y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return distance < PLAYER_SIZE * 7; // Ensure powerups are not too close to players
    });

    if (!isOverlappingWithPlayer && !isOverlapping(x, y, POWERUP_SIZE, obstacles) && !isPowerupOvelapWithEachOther(x, y,powerups,sharedObject)) {
      powerups.push({
        x,
        y,
        type: 'speed',
        active: true
      });
    }
  }

  // Generate 'slow' powerups
  while (powerups.filter(p => p.type === 'slow').length < numSpeedAndSlow) {
    const obstacle = obstacles[Math.floor(Math.random() * obstacles.length)];
    const x = Math.random() * (obstacle.x + obstacle.size);
    const y = Math.random() * (obstacle.y + obstacle.size);

    // Ensure powerups are not overlapping with players
    const isOverlappingWithPlayer = players.some(player => {
      const dx = player.x - x;
      const dy = player.y - y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return distance < PLAYER_SIZE * 3; // Ensure powerups are not too close to players
    });

    if (!isOverlappingWithPlayer && !isOverlapping(x, y, POWERUP_SIZE, obstacles) && !isPowerupOvelapWithEachOther(x, y,powerups,sharedObject)) {
      powerups.push({
        x,
        y,
        type: 'slow',
        active: true
      });
    }
  }

  return powerups;
}

const sharedObject = {
  x: CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
  y: CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
  isHeld: false,
  holderId: null
}
const players = [
  {
    id: 1,
    x: 10,
    y: 10,
    speed: BASE_SPEED,
    score: 0,
    color: 'red',
    hasObject: false,
    powerups: { speedBoost: 0, speedPenalty: 0}
  },
  {
    id: 2,
    x: CANVAS_SIZE - PLAYER_SIZE - 10,
    y: CANVAS_SIZE - PLAYER_SIZE -10 ,
    speed: BASE_SPEED,
    score: 0,
    color: 'purple',
    hasObject: false,
    powerups: { speedBoost: 0, speedPenalty: 0}
  },{
    id: 3,
    x: 10,
    y: CANVAS_SIZE-PLAYER_SIZE -10 ,
    speed: BASE_SPEED,
    score: 0,
    color: 'blue',
    hasObject: false,
    powerups: { speedBoost: 0, speedPenalty: 0}
  },
  {
    id: 4,
    x: CANVAS_SIZE - PLAYER_SIZE -10,
    y: 10,
    speed: BASE_SPEED,
    score: 0,
    color: 'green',
    hasObject: false,
    powerups: { speedBoost: 0, speedPenalty: 0}
  }
]
const obstacles = generateObstacles(players, sharedObject); 
function App() {
  const [gameState, setGameState] = useState<GameState>({
    players: players,
    sharedObject: sharedObject,
    obstacles: obstacles,
    powerups: generatePowerups(obstacles,players, sharedObject),
    timeRemaining: GAME_DURATION,
    gameStarted: false,
    winner: null
  });


  const checkCollision = useCallback(
    (playerX: number, playerY: number, playerSize: number, obstacleX: number, obstacleY: number, obstacleSize: number) => {
      // Check if the player's rectangle overlaps with the obstacle's rectangle
      return (
        playerX < obstacleX + obstacleSize &&  // Player's right side is not beyond obstacle's left side
        playerX + playerSize > obstacleX &&    // Player's left side is not beyond obstacle's right side
        playerY < obstacleY + obstacleSize &&  // Player's bottom side is not beyond obstacle's top side
        playerY + playerSize > obstacleY       // Player's top side is not beyond obstacle's bottom side
      );
    },
    []
  );

  const movePlayer = useCallback((playerId: number, dx: number, dy: number) => {
    setGameState(prev => {
      const player = prev.players.find(p => p.id === playerId)!;
      const currentTime = Date.now();
      const speedBoostActive = player.powerups.speedBoost > currentTime;
      const speedPenaltyActive = player.powerups.speedPenalty > currentTime;
  
      let speed:number=player.speed
      if(speedBoostActive){
        speed = player.speed + SPEED_BOOST
      }
      if(speedPenaltyActive){
        speed = 2
      }  
      let newX = player.x + dx * speed;
      let newY = player.y + dy * speed;
  
      // Boundary checks
      newX = Math.max(0, Math.min(CANVAS_SIZE - PLAYER_SIZE, newX));
      newY = Math.max(0, Math.min(CANVAS_SIZE - PLAYER_SIZE, newY));
  
      // Obstacle collision checks
      for (const obstacle of prev.obstacles) {
        if (checkCollision(newX, newY, PLAYER_SIZE, obstacle.x, obstacle.y, obstacle.size)) {
          newX = player.x;
          newY = player.y;
        }
      }
    // Player-to-Player collision checks
      for (const otherPlayer of prev.players) {
        if (otherPlayer.id !== playerId) {
          if (checkCollision(newX, newY, PLAYER_SIZE, otherPlayer.x, otherPlayer.y, PLAYER_SIZE)) {
            newX = player.x;
            newY = player.y;
          }
        }
      }
  
      // Powerup collection
      const newPowerups = [...prev.powerups];
      const newPlayers = [...prev.players];
      const playerIndex = newPlayers.findIndex(p => p.id === playerId);
  
      prev.powerups.forEach((powerup, index) => {
        if (powerup.active && checkCollision(newX, newY, PLAYER_SIZE, powerup.x, powerup.y, POWERUP_SIZE)) {
          newPowerups[index] = { ...powerup, active: false };
  
          switch (powerup.type) {
            case 'speed':
              newPlayers[playerIndex].powerups.speedBoost = Date.now() + 80000;
              break;
            case 'slow':
              newPlayers[playerIndex].powerups.speedPenalty = Date.now() + 100000;
              break;
          }
        }
      });
  
      let newSharedObject = { ...prev.sharedObject };
  
      // Check if player can pick up shared object
      if ( !prev.sharedObject.isHeld && checkCollision(newX, newY, PLAYER_SIZE, prev.sharedObject.x, prev.sharedObject.y, OBJECT_SIZE)
      ) {
        let newXPos: number = 0;
        let newYPos: number = 0;
        let isValidPosition = false;
  
        while (!isValidPosition) {
          // Generate random positions within bounds
          newXPos = Math.floor(Math.random() * (CANVAS_SIZE - OBJECT_SIZE));
          newYPos = Math.floor(Math.random() * (CANVAS_SIZE - OBJECT_SIZE));
  
          // Check for collisions with obstacles and powerups
          isValidPosition = !prev.obstacles.some((obstacle) =>
            checkCollision(newXPos, newYPos, OBJECT_SIZE, obstacle.x, obstacle.y, obstacle.size)
          ) && !prev.powerups.some((powerup) =>
            powerup.active && checkCollision(newXPos, newYPos, OBJECT_SIZE, powerup.x, powerup.y, POWERUP_SIZE)
          );
        }
  
        newSharedObject = {
          isHeld: false,
          holderId: null,
          x: newXPos,
          y: newYPos
        };
  
          newPlayers[playerIndex].score += 1; // Increment score when object is picked
      }
  
      // Update player position
      const updatedPlayers = newPlayers.map(p =>
        p.id === playerId ? { ...p, x: newX, y: newY} : p
      );
  
      return {
        ...prev,
        players: updatedPlayers,
        sharedObject: newSharedObject,
        powerups: newPowerups
      };
    });
  }, []);
  
  useEffect(() => {
    if (!gameState.gameStarted) return;

    const handleKeyPress = (e: KeyboardEvent) => {
      // Player 1 controls (WASD)
      if (e.key === 'w') movePlayer(1, 0, -1);
      if (e.key === 's') movePlayer(1, 0, 1);
      if (e.key === 'a') movePlayer(1, -1, 0);
      if (e.key === 'd') movePlayer(1, 1, 0);

      // Player 2 controls (Arrow keys)
      if (e.key === 'ArrowUp') movePlayer(2, 0, -1);
      if (e.key === 'ArrowDown') movePlayer(2, 0, 1);
      if (e.key === 'ArrowLeft') movePlayer(2, -1, 0);
      if (e.key === 'ArrowRight') movePlayer(2, 1, 0);
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [gameState.gameStarted, movePlayer]);

  useEffect(() => {
    if (!gameState.gameStarted) return;

    const gameLoop = setInterval(() => {
      setGameState(prev => {
        const now = Date.now();
        const newPlayers = prev.players.map(player => ({
          ...player,
          powerups: {
            speedBoost: Math.max(0, player.powerups.speedBoost - now),
            speedPenalty: Math.max(0, player.powerups.speedPenalty - now),
          }
        }));

        return {
          ...prev,
          timeRemaining: prev.timeRemaining - 1,
          players: newPlayers
        };
      });
    }, 1000);

    return () => clearInterval(gameLoop);
  }, [gameState.gameStarted]);

  useEffect(() => {
    if (gameState.timeRemaining <= 0) {
      setGameState(prev => {
        // Determine the player with the highest score
        const highestScorePlayer = prev.players.reduce((maxPlayer, player) => 
          player.score > maxPlayer.score ? player : maxPlayer
        );
    
        return {
          ...prev,
          gameStarted: false,
          winner: highestScorePlayer.id // Use the player ID as the winner
        };
      });
    }
  }, [gameState.timeRemaining]);

  const startGame = () => {
    setGameState({
      players: players,
      sharedObject: sharedObject,
      obstacles: obstacles,
      powerups: generatePowerups(obstacles,players, sharedObject),
      timeRemaining: GAME_DURATION,
      gameStarted: true,
      winner: null
    });
  };

  const getPowerupIcon = (type: string) => {
    switch (type) {
      case 'speed': return <Zap className="w-6 h-6 text-yellow-400" />;
      case 'slow': return <Snow className="w-6 h-6 text-blue-400" />;
      default: return null;
    }
  };

  const getObstacleStyle = (type: string) => {
    switch (type) {
      case 'ice': return 'bg-blue-300';
      default: return '';
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="flex flex-col items-center">
        <div className="mb-4 flex items-center gap-8">
          <div className="text-white flex items-center gap-2">
            <Timer className="w-6 h-6" />
            <span className="text-2xl font-bold">{gameState.timeRemaining}s</span>
          </div>
          {gameState.players.map(player => (
            <div
              key={player.id}
              className="flex items-center gap-2"
              style={{ color: player.color }}
            >
              <Trophy className="w-6 h-6" />
              <span className="text-2xl font-bold">Player {player.id}: {player.score}</span>
            </div>
          ))}
        </div>

        <div
          className="relative bg-gray-800 rounded-lg overflow-hidden"
          style={{ width: CANVAS_SIZE, height: CANVAS_SIZE }}
        >
          {/* Obstacles */}
          {gameState.obstacles.map((obstacle, index) => (
            <div
              key={index}
              className={`absolute rounded-lg ${getObstacleStyle(obstacle.type)}`}
              style={{
                left: obstacle.x,
                top: obstacle.y,
                width: obstacle.size,
                height: obstacle.size
              }}
            >
            </div>
          ))}

          {/* Powerups */}
          {gameState.powerups.map((powerup, index) => (
            powerup.active && (
              <div
                key={index}
                className="absolute flex items-center justify-center"
                style={{
                  left: powerup.x,
                  top: powerup.y,
                  width: POWERUP_SIZE,
                  height: POWERUP_SIZE
                }}
              >
                {getPowerupIcon(powerup.type)}
              </div>
            )
          ))}

          {/* Shared Object */}
          <div
            className="absolute bg-yellow-400 rounded-full"
            style={{
              left: gameState.sharedObject.x,
              top: gameState.sharedObject.y,
              width: OBJECT_SIZE,
              height: OBJECT_SIZE
            }}
          >
            <Star className="w-full h-full text-yellow-600" />
          </div>

          {/* Players */}
          {gameState.players.map(player => (
            <div
              key={player.id}
              className="absolute rounded-lg transition-all duration-100"
              style={{
                backgroundColor: player.color,
                left: player.x,
                top: player.y,
                width: PLAYER_SIZE,
                height: PLAYER_SIZE,
              
              }}
            />
          ))}
        </div>

        {!gameState.gameStarted && (
          <div className="mt-6 text-center">
            {gameState.winner && (
              <h2 className="text-2xl font-bold mb-4" style={{ color: gameState.players[gameState.winner - 1].color }}>
                Player {gameState.winner} Wins!
              </h2>
            )}
            <button
              onClick={startGame}
              className="px-6 py-3 bg-indigo-600 text-white rounded-lg text-xl font-bold hover:bg-indigo-700 transition-colors"
            >
              {gameState.timeRemaining === GAME_DURATION ? 'Start Game' : 'Play Again'}
            </button>
          </div>
        )}

        <div className="mt-6 text-gray-400 text-center">
          <p className="text-lg mb-2">Controls:</p>
          <p>Player 1: WASD keys</p>
          <p>Player 2: Arrow keys</p>
          <div className="mt-4 flex gap-4 justify-center">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-400" />
              <span>Speed Boost</span>
            </div>
            <div className="flex items-center gap-2">
              <Snow className="w-5 h-5 text-blue-400" />
              <span>Slow Enemy</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;


