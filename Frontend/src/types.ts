export interface Player {
  id: number;
  x: number;
  y: number;
  speed: number;
  score: number;
  color: string;

  powerups: PowerupEffects;
}

export interface PowerupEffects {
  speedBoost: number;
  speedPenalty: number;
}

export interface SharedObject {
  x: number;
  y: number;
  isHeld: boolean;
  holderId: number | null;
}

export interface Obstacle {
  x: number;
  y: number;
  size: number;
  type: 'ice';
}

export interface Powerup {
  x: number;
  y: number;
  type: 'speed' | 'slow';
  active: boolean;
}

export interface GameState {
  players: Player[];
  sharedObject: SharedObject;
  obstacles: Obstacle[];
  powerups: Powerup[];
  timeRemaining: number;
  gameStarted: boolean;
  winner: number | null;
}

export const CANVAS_SIZE = 550;
export const PLAYER_SIZE = 25;
export const OBJECT_SIZE = 30;
export const POWERUP_SIZE = 25;
export const GAME_DURATION = 60; // seconds
export const BASE_SPEED = 15;
export const SPEED_BOOST = 10;
export const SPEED_PENALTY = -30;
