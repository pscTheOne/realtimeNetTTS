import pyaudio
import webrtcvad
import threading
import wave
import requests
from sseclient import SSEClient
from ip_settings import get_ip
import time
import logging
import numpy as np
from scipy.signal import resample

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Parameters for audio stream
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000  # Original sample rate
NEW_RATE = 16000  # New sample rate for uploading and saving
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
wav_file.setframerate(NEW_RATE)

def receive_transcriptions():
    url = f'http://{SERVER_IP}:{HTTP_PORT}/transcriptions'
    messages = SSEClient(url)
    for msg in messages:
        logging.info(f"Transcription: {msg.data}")

def callback(in_data, frame_count, time_info, status):
    if True:
    #vad.is_speech(in_data, RATE):
        with data_lock:
            audio_data.append(in_data)
        resampled_data = resample_audio(np.frombuffer(in_data, dtype=np.int16))
        wav_file.writeframes(resampled_data.tobytes())  # Append resampled audio data to WAV file
    return (in_data, pyaudio.paContinue)

def start_sse_client():
    receive_transcriptions()

sse_thread = threading.Thread(target=start_sse_client)
sse_thread.start()

# Buffer to store audio data before sending
audio_data = []
data_lock = threading.Lock()

# Function to resample audio data
def resample_audio(data):
    number_of_samples = round(len(data) * float(NEW_RATE) / RATE)
    resampled_data = resample(data, number_of_samples)
    return resampled_data.astype(np.int16)

# Function to send audio data to the server
def send_audio_stream():
    url = f'http://{SERVER_IP}:{HTTP_PORT}/send_audio'
    headers = {'Content-Type': 'application/octet-stream'}
    while True:
        chunk = b''  # Initialize chunk variable
        with data_lock:
            if audio_data:
                audio_chunk = b''.join(audio_data)
                audio_data.clear()
                chunk = resample_audio(np.frombuffer(audio_chunk, dtype=np.int16)).tobytes()
        if chunk:  # Only send if there is data in the chunk
            try:
                response = requests.post(url, headers=headers, data=chunk)
                response.raise_for_status()  # Raise an error for bad responses
                logging.debug("Audio data sent successfully.")
                time.sleep(0.05)  # Adjust the sending rate to avoid overloading the server
            except Exception as e:
                logging.error(f"Error sending audio data: {e}")

# Start the audio streaming thread
audio_stream_thread = threading.Thread(target=send_audio_stream, daemon=True)
audio_stream_thread.start()

stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    stream_callback=callback)

logging.info("Listening...")
stream.start_stream()

try:
    while True:
        pass
except KeyboardInterrupt:
    logging.info("Stopping...")

stream.stop_stream()
stream.close()
audio.terminate()
wav_file.close()
