import socket
import time
import threading
from typing import Any, Callable, Dict, Optional

class TwitchChatMonitor:
    def __init__(self, channel):
        self.channel = channel
        self.sock = socket.socket()
        
    def connect(self):
        """Connect to Twitch IRC"""
        self.sock.connect(('irc.chat.twitch.tv', 6667))
        self.sock.send(f"PASS oauth:justinfan12345\n".encode('utf-8'))
        self.sock.send(f"NICK justinfan12345\n".encode('utf-8'))
        self.sock.send(f"JOIN #{self.channel}\n".encode('utf-8'))
        print(f'Connected to #{self.channel}')
        print('Listening for messages...')
        print('=' * 50)
        
    def get_messages(self):
        """Receive and parse messages"""
        response = self.sock.recv(2048).decode('utf-8', errors='ignore')
        
        # Handle PING to keep connection alive
        if response.startswith('PING'):
            self.sock.send("PONG\n".encode('utf-8'))
            return []
        
        messages = []
        for line in response.split('\r\n'):
            if 'PRIVMSG' in line:
                try:
                    # Parse username
                    username = line.split('!')[0][1:]
                    # Parse message
                    message = line.split('PRIVMSG')[1].split(':')[1]
                    messages.append((username, message))
                except:
                    pass
        
        return messages
    
    def run(self, message_callback=None):
        """Main loop with optional callback"""
        self.connect()
        
        try:
            while True:
                messages = self.get_messages()
                for username, message in messages:
                    print(f'{username}: {message}')
                    if message_callback:
                        message_callback(username, message)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nDisconnecting...")
            self.sock.close()
        except Exception as e:
            print(f"Error: {e}")
            self.sock.close()
