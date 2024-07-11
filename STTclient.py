import pyaudio
import webrtcvad
import requests
import threading
from sseclient import SSEClient
from ip_settings import get_ip

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Parameters for audio stream
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 960
SERVER_IP = get_ip()
SERVER_PORT = 5000

# Initialize WebRTC VAD
vad = webrtcvad.Vad()
vad.set_mode(1)

def send_audio_data(audio_data):
    requests.post(f'http://{SERVER_IP}:{SERVER_PORT}/send_audio', data=audio_data)

def receive_transcriptions():
    url = f'http://{SERVER_IP}:{SERVER_PORT}/transcriptions'
    messages = SSEClient(url)
    for msg in messages:
        print(f"Transcription: {msg.data}")

def callback(in_data, frame_count, time_info, status):
    if vad.is_speech(in_data, RATE):
        send_audio_data(in_data)
    return (in_data, pyaudio.paContinue)

stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=callback)

def start_sse_client():
    receive_transcriptions()

sse_thread = threading.Thread(target=start_sse_client)
sse_thread.start()

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
