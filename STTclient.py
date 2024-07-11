import pyaudio
import webrtcvad
import socket
import threading
import json
import wave
import requests
import asyncio
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from sseclient import SSEClient
from ip_settings import get_ip

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Parameters for audio stream
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000  # Updated sample rate
CHUNK = 960  # 20ms frames for 48000 Hz
BATCH_SIZE = 5  # Number of chunks to batch together
GAIN = 2.0  # Gain factor to amplify the audio
SERVER_IP = get_ip()
SERVER_PORT = 5000

# Initialize WebRTC VAD
vad = webrtcvad.Vad()
vad.set_mode(1)  # 0: least aggressive, 3: most aggressive

# Open a WAV file to append audio data
wav_file = wave.open("recorded_audio.wav", 'wb')
wav_file.setnchannels(CHANNELS)
wav_file.setsampwidth(audio.get_sample_size(FORMAT))
wav_file.setframerate(RATE)

audio_buffer = []
executor = ThreadPoolExecutor(max_workers=1)

def amplify_audio(audio_data, gain):
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    audio_array = np.clip(audio_array * gain, -32768, 32767)
    return audio_array.astype(np.int16).tobytes()

def send_audio_data(audio_data):
    url = f'http://{SERVER_IP}:{SERVER_PORT}/send_audio'
    headers = {'Content-Type': 'application/octet-stream'}
    response = requests.post(url, headers=headers, data=audio_data)
    if response.status_code != 200:
        print(f"Failed to send audio data: {response.status_code} - {response.text}")

async def async_send_audio_data():
    loop = asyncio.get_event_loop()
    while True:
        if audio_buffer:
            batch = b''.join(audio_buffer)
            audio_buffer.clear()
            await loop.run_in_executor(executor, send_audio_data, batch)
        await asyncio.sleep(0.1)

def receive_transcriptions():
    url = f'http://{SERVER_IP}:{SERVER_PORT}/transcriptions'
    messages = SSEClient(url)
    for msg in messages:
        print(f"Transcription: {msg.data}")

def callback(in_data, frame_count, time_info, status):
    if vad.is_speech(in_data, RATE):
        amplified_data = amplify_audio(in_data, GAIN)
        audio_buffer.append(amplified_data)
        wav_file.writeframes(amplified_data)  # Append audio data to WAV file
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

asyncio.run(async_send_audio_data())

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
sock.close()
