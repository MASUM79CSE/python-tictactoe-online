from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
import json
import uuid

app = FastAPI()

class TicTacToeGame:
    def __init__(self):
        self.board = [["" for _ in range(3)] for _ in range(3)]
        self.current_player = "X"
        self.winner = None
        self.is_draw = False
    
    def make_move(self, row: int, col: int) -> bool:
        if self.board[row][col] == "" and not self.winner:
            self.board[row][col] = self.current_player
            if self.check_winner(row, col):
                self.winner = self.current_player
            elif self.is_board_full():
                self.is_draw = True
            else:
                self.current_player = "O" if self.current_player == "X" else "X"
            return True
        return False
    
    def check_winner(self, row: int, col: int) -> bool:
        # Check row
        if all(self.board[row][i] == self.current_player for i in range(3)):
            return True
        # Check column
        if all(self.board[i][col] == self.current_player for i in range(3)):
            return True
        # Check diagonals
        if row == col and all(self.board[i][i] == self.current_player for i in range(3)):
            return True
        if row + col == 2 and all(self.board[i][2-i] == self.current_player for i in range(3)):
            return True
        return False
    
    def is_board_full(self) -> bool:
        return all(cell != "" for row in self.board for cell in row)
    
    def get_state(self) -> dict:
        return {
            "board": self.board,
            "currentPlayer": self.current_player,
            "winner": self.winner,
            "isDraw": self.is_draw
        }

class GameManager:
    def __init__(self):
        self.games: Dict[str, TicTacToeGame] = {}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}
    
    def create_game(self) -> str:
        game_id = str(uuid.uuid4())
        self.games[game_id] = TicTacToeGame()
        self.connections[game_id] = {}
        return game_id
    
    def get_game(self, game_id: str) -> Optional[TicTacToeGame]:
        return self.games.get(game_id)

game_manager = GameManager()

@app.get("/")
async def read_root():
    return {"message": "Tic-Tac-Toe Server is running"}

@app.post("/create-game")
async def create_game():
    game_id = game_manager.create_game()
    return {"gameId": game_id}

@app.websocket("/ws/{game_id}/{player}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player: str):
    game = game_manager.get_game(game_id)
    if not game:
        await websocket.close()
        return
    
    await websocket.accept()
    game_manager.connections[game_id][player] = websocket
    
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "move":
                row, col = data["row"], data["col"]
                if game.make_move(row, col):
                    # Broadcast game state to all players
                    state = game.get_state()
                    for conn in game_manager.connections[game_id].values():
                        await conn.send_json(state)
    
    except WebSocketDisconnect:
        if game_id in game_manager.connections:
            if player in game_manager.connections[game_id]:
                del game_manager.connections[game_id][player]