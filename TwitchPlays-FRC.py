import socket
import time
import threading
from typing import Any, Callable, Dict, Optional
from ntcore import NetworkTableInstance, NetworkTableEntry

from .twitchchat import TwitchChatMonitor
from .networktable import 

# Configuration
TWITCH_CHANNEL = 'ryanforce_'  # Change this to your desired channel (without #)
COMMAND_DURATION = 1.0  # Duration in seconds to hold each command

class TwitchToNetworkTables:
    def __init__(self, channel=TWITCH_CHANNEL, command_duration=COMMAND_DURATION):
        commands = {
            'forward': ('LeftY', 1.0, 0.0),
            'backward': ('LeftY', -1.0, 0.0),
            'back': ('LeftY', -1.0, 0.0),
            'left': ('LeftX', -1.0, 0.0),
            'right': ('LeftX', 1.0, 0.0),
            'l': ('RightX', -1.0, 0.0),
            'r': ('RightX', 1.0, 0.0),
            'l4': ('L4', True, False),
            'l3': ('L3', True, False),
            'l2': ('L2', True, False),
            'l1': ('L1', True, False),
            'intake': ('Intake', True, False),
            'stop': ('LeftY', 0.0, 0.0),  # Emergency stop
        }
        self.monitor = TwitchChatMonitor(channel)
        self.handler = NetworkTableHandler(command_map=commands command_duration=command_duration)
        
    def on_message(self, username: str, message: str):
        """Callback for when a message is received"""
        self.handler.process_command(username, message)
    
    def run(self):
        """Start the system"""
        print("Starting Twitch to NetworkTables bridge...")
        print(f"Command duration: {self.handler.command_duration}s")
        print("\nAvailable commands:")
        for cmd in sorted(self.handler.command_map.keys()):
            print(f"  - {cmd}")
        print("\n" + "=" * 50)
        
        try:
            self.monitor.run(message_callback=self.on_message)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.handler.cancel_all()
            self.handler.smart_nt.stop()

if __name__ == "__main__":
    bridge = TwitchToNetworkTables()
    bridge.run()
