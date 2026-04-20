from typing import Dict, List, Optional


class GameRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: List[int] = []   # telegram_id list
        self.state: dict = {}          # game state payload (to be defined per game)
        self.is_started: bool = False

    def is_full(self, max_players: int = 2) -> bool:
        return len(self.players) >= max_players

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "players": self.players,
            "is_started": self.is_started,
        }


class GameManager:
    """Manages multiplayer game rooms. Designed to plug into python-socketio or FastAPI WebSockets."""

    def __init__(self):
        self._rooms: Dict[str, GameRoom] = {}
        self._player_room: Dict[int, str] = {}  # telegram_id -> room_id

    # ------------------------------------------------------------------
    def create_room(self, room_id: str) -> GameRoom:
        if room_id in self._rooms:
            return self._rooms[room_id]
        room = GameRoom(room_id)
        self._rooms[room_id] = room
        return room

    def join_room(self, room_id: str, player_id: int) -> Optional[GameRoom]:
        """Add player to room. Returns None if room is full or doesn't exist."""
        room = self._rooms.get(room_id)
        if room is None or room.is_full():
            return None
        if player_id not in room.players:
            room.players.append(player_id)
            self._player_room[player_id] = room_id
        return room

    def leave_room(self, player_id: int) -> Optional[str]:
        """Remove player from their current room. Returns room_id if found."""
        room_id = self._player_room.pop(player_id, None)
        if room_id and room_id in self._rooms:
            room = self._rooms[room_id]
            if player_id in room.players:
                room.players.remove(player_id)
            if not room.players:
                del self._rooms[room_id]
        return room_id

    def get_room(self, room_id: str) -> Optional[GameRoom]:
        return self._rooms.get(room_id)

    def get_player_room(self, player_id: int) -> Optional[GameRoom]:
        room_id = self._player_room.get(player_id)
        return self._rooms.get(room_id) if room_id else None

    def list_open_rooms(self) -> List[dict]:
        return [r.to_dict() for r in self._rooms.values() if not r.is_full() and not r.is_started]


# Singleton instance — import this in main.py when wiring up WebSocket/socketio events
game_manager = GameManager()
