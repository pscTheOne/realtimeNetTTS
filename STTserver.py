import socket
import threading
from flask import Flask, jsonify
from RealtimeSTT import AudioToTextRecorder

app = Flask(__name__)

# Server IP and port for UDP listener
SERVER_IP = '0.0.0.0'
SERVER_PORT = 12345

# Initialize AudioToTextRecorder with microphone usage disabled
recorder = AudioToTextRecorder(use_microphone=False)

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((SERVER_IP, SERVER_PORT))

transcriptions = []

def udp_listener():
    while True:
        data, addr = sock.recvfrom(1024)
        if data:
            recorder.feed_audio(data)
            transcription = recorder.get_latest_transcription()
            if transcription:
                transcriptions.append(transcription)

@app.route('/get_transcription', methods=['GET'])
def get_transcription():
    if transcriptions:
        return jsonify({"transcription": transcriptions.pop(0)})
    return jsonify({"transcription": ""})

if __name__ == '__main__':
    udp_thread = threading.Thread(target=udp_listener)
    udp_thread.start()
    app.run(debug=True, host='0.0.0.0', port=5000)
