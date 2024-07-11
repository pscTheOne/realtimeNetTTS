import pyaudio
import webrtcvad
import socket
import requests
import threading
import time
from ip_settings import get_ip

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Parameters for audio stream
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 960
SERVER_IP = get_ip()
SERVER_PORT = 12346  # Changed port
API_URL = f'http://{SERVER_IP}:5000/get_transcription'

# Initialize WebRTC VAD
vad = webrtcvad.Vad()
vad.set_mode(1)

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_audio_data(audio_data):
    sock.sendto(audio_data, (SERVER_IP, SERVER_PORT))

def get_transcription():
    response = requests.get(API_URL)
    if response.status_code == 200:
        transcription = response.json().get('transcription')
        if transcription:
            print(f"Transcription: {transcription}")

def callback(in_data, frame_count, time_info, status):
    if vad.is_speech(in_data, RATE):
        send_audio_data(in_data)
    return (in_data, pyaudio.paContinue)

# Open audio stream
stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=callback)

def polling_transcription():
    while True:
        get_transcription()
        time.sleep(1)

polling_thread = threading.Thread(target=polling_transcription)
polling_thread.start()

print("Listening...")
stream.start_stream()

try:
    while True:
        pass
except KeyboardInterrupt:
    print("Stopping...")

stream.stop_stream()
stream.close()
audio.terminate()
sock.close()
