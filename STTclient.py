import pyaudio
import webrtcvad
import socket
import threading
import json
import wave
import requests
from sseclient import SSEClient
from ip_settings import get_ip

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Parameters for audio stream
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000  # Updated sample rate
CHUNK = 960  # 20ms frames for 48000 Hz
SERVER_IP = get_ip()
HTTP_PORT = 5000

# Initialize WebRTC VAD
vad = webrtcvad.Vad()
vad.set_mode(1)  # 0: least aggressive, 3: most aggressive

# Open a WAV file to append audio data
wav_file = wave.open("recorded_audio.wav", 'wb')
wav_file.setnchannels(CHANNELS)
wav_file.setsampwidth(audio.get_sample_size(FORMAT))
wav_file.setframerate(RATE)

def receive_transcriptions():
    url = f'http://{SERVER_IP}:{HTTP_PORT}/transcriptions'
    messages = SSEClient(url)
    for msg in messages:
        print(f"Transcription: {msg.data}")

def send_audio_data(audio_data):
    try:
        url = f'http://{SERVER_IP}:{HTTP_PORT}/send_audio'
        headers = {'Content-Type': 'application/octet-stream'}
        response = requests.post(url, headers=headers, data=audio_data)
        if response.status_code != 200:
            print(f"Failed to send audio data: {response.status_code}")
    except Exception as e:
        print(f"Exception in sending audio data: {e}")

def callback(in_data, frame_count, time_info, status):
    if vad.is_speech(in_data, RATE):
        send_audio_data(in_data)
        wav_file.writeframes(in_data)  # Append audio data to WAV file
    return (in_data, pyaudio.paContinue)

def start_sse_client():
    receive_transcriptions()

sse_thread = threading.Thread(target=start_sse_client)
sse_thread.start()

stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=callback)

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
wav_file.close()
