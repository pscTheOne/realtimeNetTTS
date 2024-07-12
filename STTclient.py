import pyaudio
import webrtcvad
import threading
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

def callback(in_data, frame_count, time_info, status):
    if vad.is_speech(in_data, RATE):
        with data_lock:
            audio_data.append(in_data)
        wav_file.writeframes(in_data)  # Append audio data to WAV file
    return (in_data, pyaudio.paContinue)

def start_sse_client():
    receive_transcriptions()

sse_thread = threading.Thread(target=start_sse_client)
sse_thread.start()

# Buffer to store audio data before sending
audio_data = []
data_lock = threading.Lock()

# Function to send audio data to the server
def send_audio_stream():
    url = f'http://{SERVER_IP}:{HTTP_PORT}/send_audio'
    headers = {'Content-Type': 'application/octet-stream'}
    while True:
        chunk = b''  # Initialize chunk variable
        with data_lock:
            if audio_data:
                chunk = b''.join(audio_data)
                audio_data.clear()
        if chunk:  # Only send if there is data in the chunk
            try:
                requests.post(url, headers=headers, data=chunk)
            except Exception as e:
                print(f"Error sending audio data: {e}")

# Start the audio streaming thread
audio_stream_thread = threading.Thread(target=send_audio_stream, daemon=True)
audio_stream_thread.start()

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
