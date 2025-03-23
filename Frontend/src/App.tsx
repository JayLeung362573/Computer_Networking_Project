import React, { useEffect, useState, useCallback } from 'react';
import { Timer, Trophy, Star, Zap, SunSnow as Snow, Shield, Ghost } from 'lucide-react';
import {
  Player, SharedObject, GameState, Obstacle, Powerup,
  CANVAS_SIZE, PLAYER_SIZE, OBJECT_SIZE, POWERUP_SIZE,
  GAME_DURATION, BASE_SPEED, SPEED_BOOST, SPEED_PENALTY,
  FREEZE_DURATION, INVINCIBLE_DURATION
} from './types';

const NUM_OBSTACLES = 6;
const NUM_POWERUPS = 4;

function generateObstacles(): Obstacle[] {
  const types: ('wall' | 'mud' | 'ice')[] = ['wall', 'mud', 'ice'];
  return Array(NUM_OBSTACLES).fill(null).map(() => ({
    x: Math.random() * (CANVAS_SIZE - PLAYER_SIZE * 2),
    y: Math.random() * (CANVAS_SIZE - PLAYER_SIZE * 2),
    size: PLAYER_SIZE * 2,
    type: types[Math.floor(Math.random() * types.length)]
  }));
}

function generatePowerups(): Powerup[] {
  const types: ('speed' | 'slow' | 'freeze' | 'invincible')[] = ['speed', 'slow', 'freeze', 'invincible'];
  return Array(NUM_POWERUPS).fill(null).map(() => ({
    x: Math.random() * (CANVAS_SIZE - POWERUP_SIZE),
    y: Math.random() * (CANVAS_SIZE - POWERUP_SIZE),
    type: types[Math.floor(Math.random() * types.length)],
    active: true
  }));
}

function App() {
  const [gameState, setGameState] = useState<GameState>({
    players: [
      {
        id: 1,
        x: 50,
        y: 50,
        speed: BASE_SPEED,
        score: 0,
        color: '#FF6B6B',
        hasObject: false,
        powerups: { speedBoost: 0, speedPenalty: 0, freezeTimer: 0, invincibility: 0 }
      },
      {
        id: 2,
        x: CANVAS_SIZE - 80,
        y: CANVAS_SIZE - 80,
        speed: BASE_SPEED,
        score: 0,
        color: '#4ECDC4',
        hasObject: false,
        powerups: { speedBoost: 0, speedPenalty: 0, freezeTimer: 0, invincibility: 0 }
      }
    ],
    sharedObject: {
      x: CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
      y: CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
      isHeld: false,
      holderId: null
    },
    obstacles: generateObstacles(),
    powerups: generatePowerups(),
    timeRemaining: GAME_DURATION,
    gameStarted: false,
    winner: null
  });

  const checkCollision = useCallback((x1: number, y1: number, w1: number, x2: number, y2: number, w2: number) => {
    return x1 < x2 + w2 && x1 + w1 > x2 && y1 < y2 + w2 && y1 + w1 > y2;
  }, []);

  const movePlayer = useCallback((playerId: number, dx: number, dy: number) => {
    setGameState(prev => {
      const player = prev.players.find(p => p.id === playerId)!;
      
      // Check if player is frozen
      if (player.powerups.freezeTimer > 0) return prev;

      const speed = player.speed * 
        (1 + (player.powerups.speedBoost > 0 ? SPEED_BOOST : 0)) *
        (player.powerups.speedPenalty > 0 ? SPEED_PENALTY : 1);

      let newX = player.x + dx * speed;
      let newY = player.y + dy * speed;

      // Boundary checks
      newX = Math.max(0, Math.min(CANVAS_SIZE - PLAYER_SIZE, newX));
      newY = Math.max(0, Math.min(CANVAS_SIZE - PLAYER_SIZE, newY));

      // Obstacle collision checks
      for (const obstacle of prev.obstacles) {
        if (checkCollision(newX, newY, PLAYER_SIZE, obstacle.x, obstacle.y, obstacle.size)) {
          if (obstacle.type === 'wall' && player.powerups.invincibility === 0) {
            return prev; // Can't move through walls unless invincible
          } else if (obstacle.type === 'mud') {
            newX = player.x + (dx * speed * 0.5);
            newY = player.y + (dy * speed * 0.5);
          } else if (obstacle.type === 'ice') {
            newX = player.x + (dx * speed * 1.5);
            newY = player.y + (dy * speed * 1.5);
          }
        }
      }

      // Powerup collection
      const newPowerups = [...prev.powerups];
      prev.powerups.forEach((powerup, index) => {
        if (powerup.active && checkCollision(newX, newY, PLAYER_SIZE, powerup.x, powerup.y, POWERUP_SIZE)) {
          newPowerups[index] = { ...powerup, active: false };
          const newPlayers = [...prev.players];
          const playerIndex = newPlayers.findIndex(p => p.id === playerId);
          
          switch (powerup.type) {
            case 'speed':
              newPlayers[playerIndex].powerups.speedBoost = Date.now() + 5000;
              break;
            case 'slow':
              const otherPlayerIndex = playerIndex === 0 ? 1 : 0;
              newPlayers[otherPlayerIndex].powerups.speedPenalty = Date.now() + 3000;
              break;
            case 'freeze':
              const freezeTarget = playerIndex === 0 ? 1 : 0;
              newPlayers[freezeTarget].powerups.freezeTimer = Date.now() + FREEZE_DURATION;
              break;
            case 'invincible':
              newPlayers[playerIndex].powerups.invincibility = Date.now() + INVINCIBLE_DURATION;
              break;
          }
          return { ...prev, players: newPlayers, powerups: newPowerups };
        }
      });

      // Update shared object position if held
      let newSharedObject = { ...prev.sharedObject };
      if (player.hasObject) {
        newSharedObject = {
          ...newSharedObject,
          x: newX + PLAYER_SIZE / 2 - OBJECT_SIZE / 2,
          y: newY + PLAYER_SIZE / 2 - OBJECT_SIZE / 2
        };
      }

      // Check if player can pick up shared object
      if (!prev.sharedObject.isHeld &&
          checkCollision(newX, newY, PLAYER_SIZE, prev.sharedObject.x, prev.sharedObject.y, OBJECT_SIZE)) {
        newSharedObject = {
          ...newSharedObject,
          isHeld: true,
          holderId: playerId
        };
        
        const newPlayers = prev.players.map(p =>
          p.id === playerId ? { ...p, hasObject: true, score: p.score + 1 } : p
        );
        
        return {
          ...prev,
          players: newPlayers,
          sharedObject: newSharedObject
        };
      }

      const newPlayers = prev.players.map(p =>
        p.id === playerId ? { ...p, x: newX, y: newY } : p
      );

      return {
        ...prev,
        players: newPlayers,
        sharedObject: newSharedObject,
        powerups: newPowerups
      };
    });
  }, [checkCollision]);

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
            freezeTimer: Math.max(0, player.powerups.freezeTimer - now),
            invincibility: Math.max(0, player.powerups.invincibility - now)
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
      setGameState(prev => ({
        ...prev,
        gameStarted: false,
        winner: prev.players[0].score > prev.players[1].score ? 1 : 2
      }));
    }
  }, [gameState.timeRemaining]);

  const startGame = () => {
    setGameState({
      players: [
        {
          id: 1,
          x: 50,
          y: 50,
          speed: BASE_SPEED,
          score: 0,
          color: '#FF6B6B',
          hasObject: false,
          powerups: { speedBoost: 0, speedPenalty: 0, freezeTimer: 0, invincibility: 0 }
        },
        {
          id: 2,
          x: CANVAS_SIZE - 80,
          y: CANVAS_SIZE - 80,
          speed: BASE_SPEED,
          score: 0,
          color: '#4ECDC4',
          hasObject: false,
          powerups: { speedBoost: 0, speedPenalty: 0, freezeTimer: 0, invincibility: 0 }
        }
      ],
      sharedObject: {
        x: CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
        y: CANVAS_SIZE / 2 - OBJECT_SIZE / 2,
        isHeld: false,
        holderId: null
      },
      obstacles: generateObstacles(),
      powerups: generatePowerups(),
      timeRemaining: GAME_DURATION,
      gameStarted: true,
      winner: null
    });
  };

  const getPowerupIcon = (type: string) => {
    switch (type) {
      case 'speed': return <Zap className="w-6 h-6 text-yellow-400" />;
      case 'slow': return <Snow className="w-6 h-6 text-blue-400" />;
      case 'freeze': return <Snow className="w-6 h-6 text-cyan-400" />;
      case 'invincible': return <Shield className="w-6 h-6 text-purple-400" />;
      default: return null;
    }
  };

  const getObstacleStyle = (type: string) => {
    switch (type) {
      case 'wall': return 'bg-gray-700';
      case 'mud': return 'bg-brown-600';
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
              {obstacle.type === 'wall' && <Ghost className="w-6 h-6 text-gray-600" />}
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
                opacity: player.powerups.freezeTimer > 0 ? 0.5 : 1,
                boxShadow: player.powerups.invincibility > 0 ? '0 0 10px 5px rgba(147, 51, 234, 0.5)' : 'none'
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
            <div className="flex items-center gap-2">
              <Snow className="w-5 h-5 text-cyan-400" />
              <span>Freeze</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-purple-400" />
              <span>Invincible</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;