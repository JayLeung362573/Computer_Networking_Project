export interface Player {
  id: number;
  x: number;
  y: number;
  speed: number;
  score: number;
  color: string;
  hasObject: boolean;
  powerups: PowerupEffects;
}

export interface PowerupEffects {
  speedBoost: number;
  speedPenalty: number;
  freezeTimer: number;
  invincibility: number;
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
  type: 'wall' | 'mud' | 'ice';
}

export interface Powerup {
  x: number;
  y: number;
  type: 'speed' | 'slow' | 'freeze' | 'invincible';
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

export const CANVAS_SIZE = 800;
export const PLAYER_SIZE = 30;
export const OBJECT_SIZE = 20;
export const POWERUP_SIZE = 25;
export const GAME_DURATION = 60; // seconds
export const BASE_SPEED = 5;
export const SPEED_BOOST = 2;
export const SPEED_PENALTY = 0.5;
export const FREEZE_DURATION = 3000; // milliseconds
export const INVINCIBLE_DURATION = 5000; // milliseconds