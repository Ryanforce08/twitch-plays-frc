import threading
import time
from typing import Any

from ntcore import NetworkTableEntry, NetworkTableInstance

# command -> (key, active value, reset value)
CommandMap = dict[str, tuple[str, Any, Any]]


class NetworkTableHandler:
    """Owns the NetworkTables connection and turns chat commands into entry writes."""

    def __init__(
        self,
        table_name: str = "SmartDashboard",
        command_map: CommandMap = None,
        command_duration: float = 1.0,
        server: str = "127.0.0.1",
        client_name: str = "TwitchPlaysFRC",
        verbose: bool = True,
    ):
        self.verbose = verbose
        self.command_duration = command_duration
        self.command_map: CommandMap = dict(command_map or {})

        self.nt = NetworkTableInstance.getDefault()
        self.nt.startClient4(client_name)
        self.nt.setServer(server)
        self.table = self.nt.getTable(table_name.strip("/"))

        self._entries: dict[str, NetworkTableEntry] = {}
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

        for key, _value, reset_value in self.command_map.values():
            self.put(key, reset_value)

    # --- NetworkTables access -------------------------------------------------

    def _entry(self, key: str) -> NetworkTableEntry:
        key = str(key)
        if key not in self._entries:
            *path, name = key.strip("/").split("/")
            table = self.table
            for part in path:
                table = table.getSubTable(part)
            self._entries[key] = table.getEntry(name)
            self._log(f"created entry {key}")
        return self._entries[key]

    def put(self, key: str, value: Any):
        entry = self._entry(key)
        # bool must be checked before int/float: bool is a subclass of int.
        if isinstance(value, bool):
            entry.setBoolean(value)
        elif isinstance(value, (int, float)):
            entry.setDouble(float(value))
        elif isinstance(value, str):
            entry.setString(value)
        else:
            raise TypeError(f"Unsupported value type for '{key}': {type(value)}")
        self._log(f"set {key} = {value!r}")

    def get(self, key: str, default: Any) -> Any:
        entry = self._entry(key)
        if isinstance(default, bool):
            return entry.getBoolean(default)
        if isinstance(default, (int, float)):
            return entry.getDouble(float(default))
        if isinstance(default, str):
            return entry.getString(default)
        raise TypeError(f"Unsupported default type for '{key}': {type(default)}")

    def get_number(self, key: str, default: float = 0.0) -> float:
        return float(self.get(key, float(default)))

    def get_boolean(self, key: str, default: bool = False) -> bool:
        return bool(self.get(key, bool(default)))

    def get_string(self, key: str, default: str = "") -> str:
        return str(self.get(key, str(default)))

    def _log(self, message: str):
        if self.verbose:
            print(f"[NT] {message}")

    # --- Command handling -----------------------------------------------------

    def _lookup(self, message: str):
        """Return (key, value, reset_value) for a chat message, or None."""
        return self.command_map.get(message.lower().strip())

    def set_temporary_value(
        self, key: str, value: Any, reset_value: Any, runtime: float
    ):
        """Set a value, then reset it after command_duration seconds."""
        with self._lock:
            existing = self._timers.pop(key, None)
            if existing:
                existing.cancel()

            self.put(key, value)
            self._log(f"holding {key} = {value!r} for {self.command_duration}s")

            if runtime is None:
                runtime = self.command_duration
            timer = threading.Timer(runtime, self._reset_value, args=(key, reset_value))
            self._timers[key] = timer
            timer.start()

    def _reset_value(self, key: str, reset_value: Any):
        with self._lock:
            self.put(key, reset_value)
            self._timers.pop(key, None)

    def process_temp_command(self, username: str, message: str, runtime=None):
        """Run a chat message as a timed command."""
        command = self._lookup(message)
        if command is None:
            return
        self._log(f"{username} executed: {message.lower().strip()}")
        self.set_temporary_value(*command, runtime=runtime)

    def process_until_command(
        self, username: str, message: str, until_key: str, poll_period: float = 0.2
    ):
        """Run a chat message as a command that holds until until_key goes true."""
        command = self._lookup(message)
        if command is None:
            return
        key, value, reset_value = command

        with self._lock:
            self.put(key, value)
        self._log(f"{username} executed: {message.lower().strip()} (until {until_key})")

        def monitor():
            while True:
                try:
                    if self.get_boolean(until_key, False):
                        with self._lock:
                            self.put(key, reset_value)
                        self._log(f"reset {key} ({until_key} met)")
                        return
                except Exception as e:
                    self._log(f"monitor error for '{until_key}': {e}")
                time.sleep(poll_period)

        threading.Thread(target=monitor, daemon=True).start()

    def cancel_all(self):
        """Cancel pending resets and put every mapped key back to its reset value."""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
            for key, _value, reset_value in self.command_map.values():
                self.put(key, reset_value)
