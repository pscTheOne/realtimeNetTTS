import pyaudio
import webrtcvad
import socket
import websocket
import threading
import json

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Parameters for audio stream
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000  # Updated sample rate
CHUNK = 960  # 20ms frames for 48000 Hz
SERVER_IP = 'your_server_ip'
SERVER_PORT = 12345
WS_SERVER_URL = 'ws://your_server_ip:5000/socket.io/'

# Initialize WebRTC VAD
vad = webrtcvad.Vad()
vad.set_mode(1)  # 0: least aggressive, 3: most aggressive

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# WebSocket client
def on_message(ws, message):
    data = json.loads(message)
    print(f"Received transcription: {data['text']}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws):
    print("WebSocket connection closed")

def on_open(ws):
    print("WebSocket connection opened")

ws = websocket.WebSocketApp(WS_SERVER_URL,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)
ws.on_open = on_open

def run_ws():
    ws.run_forever()

ws_thread = threading.Thread(target=run_ws)
ws_thread.start()

# Callback function to process audio stream
def callback(in_data, frame_count, time_info, status):
    try:
        is_speech = vad.is_speech(in_data, RATE)
        if is_speech:
            sock.sendto(in_data, (SERVER_IP, SERVER_PORT))
    except webrtcvad.VadError as e:
        print(f"Error while processing frame: {e}")
    return (in_data, pyaudio.paContinue)

# Open audio stream
stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=callback)

print("Listening...")

# Start the stream
stream.start_stream()

# Keep the stream running
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Stopping...")

# Stop and close the stream
stream.stop_stream()
stream.close()

# Terminate PyAudio
audio.terminate()

# Close the WebSocket
ws.close()
ws_thread.join()
