import socket
import asyncio
import signal
import time
from flask import Flask
from flask_socketio import SocketIO
from RealtimeSTT import AudioToTextRecorder

app = Flask(__name__)
socketio = SocketIO(app)

# Server IP and port for UDP listener
SERVER_IP = '0.0.0.0'
SERVER_PORT = 12345

# Initialize AudioToTextRecorder with microphone usage disabled
recorder = AudioToTextRecorder(use_microphone=False)

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Attempt to bind the socket with retries
for _ in range(5):  # retry 5 times
    try:
        sock.bind((SERVER_IP, SERVER_PORT))
        break
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print("Address already in use, retrying in 5 seconds...")
            time.sleep(5)
        else:
            raise
else:
    raise OSError("Could not bind the socket after multiple attempts.")

def process_text(text):
    print(f"Transcribed text: {text}")
    socketio.emit('transcription', {'text': text})

async def udp_listener():
    while True:
        data, addr = sock.recvfrom(1024)
        if data:
            recorder.feed_audio(data)

def cleanup():
    print("Cleaning up resources...")
    sock.close()
    loop.stop()
    print("Server has been stopped and resources released.")

def handle_signal(signal, frame):
    asyncio.run_coroutine_threadsafe(cleanup(), loop)

if __name__ == "__main__":
    recorder.on_realtime_transcription_update = process_text
    loop = asyncio.get_event_loop()
    loop.create_task(udp_listener())

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))
        loop.close()
