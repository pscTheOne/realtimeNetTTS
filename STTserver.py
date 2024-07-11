from flask import Flask, Response, request
from RealtimeSTT import AudioToTextRecorder
import time

app = Flask(__name__)
recorder = AudioToTextRecorder(use_microphone=False)
transcriptions = []

@app.route('/send_audio', methods=['POST'])
def send_audio():
    audio_data = request.data
    recorder.feed_audio(audio_data)
    return "Success", 200

def generate_transcriptions():
    while True:
        if transcriptions:
            transcription = transcriptions.pop(0)
            yield f"data: {transcription}\n\n"
        time.sleep(1)

@app.route('/transcriptions')
def transcriptions_stream():
    return Response(generate_transcriptions(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
