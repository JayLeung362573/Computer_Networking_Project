# ⭐ Capture The Star (CMPT 371)
Created By: Puneet, Franoll, Gurshan and Jiawei

## 🎮 Project Overview

**Capture The Star** is a fast-paced online multiplayer game where players compete to collect as many stars as possible within a short time limit. Using grid-based movement with **WASD** or **Arrow keys**, players must chase and capture a **yellow star** or the *rare* and highly coveted **red star**.

- ⏱️ **Game Duration**: 30–40 seconds per round  
- 🏆 **Objective**: Player with the most captured stars at the end of the game wins  
- 🌟 **Red Star = Shared Object**: Rare, high-value, and synchronously accessed

[Gameplay Footage](https://www.youtube.com/watch?v=mhVdACm6OCg)

---

## 🛠️ How It Works

### 🧩 Client-Server Model

The game is built using a **client-server architecture**:

- **Server**:  
  - Run using `server.py`
  - Listens on a port specified by the user
  - Handles client connections using Python's `socket` and `threading` modules

- **Client**:  
  - Run using `game.py`
  - Uses **Pygame** for rendering and input
  - Automatically connects to the server on the specified IP and port

---

### 🔄 Shared Object & Concurrency Control

The **red star** acts as a **shared object**, meaning all connected players may attempt to capture it at the same time. To avoid race conditions and maintain consistent game state:

- A **mutex lock** (`threading.Lock`) is used to ensure **thread-safe** access
- Each player's interaction is managed by a **separate thread**
- Locking ensures that only one player can successfully collect the red star at a time

This ensures accurate scoring and fair play across all clients.

---

## 🧪 How to Run

### Requirements
- Python 3.x
- `pygame` (install via `pip install pygame`)

### 1. Start the Server
```bash
python server.py 
```

### 2. Start the game
```bash
python game.py 
```