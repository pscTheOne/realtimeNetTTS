import socket
import asyncio
import signal
from flask import Flask
from flask_socketio import SocketIO
from RealtimeSTT import AudioToTextRecorder

app = Flask(__name__)
socketio = SocketIO(app)

# Server IP and port for UDP listener
SERVER_IP = '0.0.0.0'
SERVER_PORT = 12346

# Initialize RealtimeSTT
stt = AudioToTextRecorder()

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((SERVER_IP, SERVER_PORT))

def process_text(text):
    print(f"Transcribed text: {text}")
    socketio.emit('transcription', {'text': text})

async def udp_listener():
    while True:
        data, addr = sock.recvfrom(1024)
        if data:
            stt.feed_audio(data)

def cleanup():
    print("Cleaning up resources...")
    sock.close()
    loop.stop()
    print("Server has been stopped and resources released.")

def handle_signal(signal, frame):
    asyncio.run_coroutine_threadsafe(cleanup(), loop)

if __name__ == "__main__":
    stt.on_realtime_transcription_update = process_text
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
