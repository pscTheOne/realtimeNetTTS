import asyncio
import signal
from contextlib import suppress
from quart import Quart, request, Response, jsonify
from RealtimeSTT import AudioToTextRecorder
import wave
import logging
import os
import threading

app = Quart(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
recorder_ready = threading.Event()
recorder = None
recorder_config = {
    'spinner': False,
    'use_microphone': False,
    'model': "base.en",
    'language': 'en',
    'silero_sensitivity': 0.4,
    'webrtc_sensitivity': 2,
    #'post_speech_silence_duration': 0.7,
    #'min_length_of_recording': 0,
    #'min_gap_between_recordings': 0
}

transcriptions = []

def recorder_thread():
    global recorder
    print("Initializing RealtimeSTT...")
    recorder = AudioToTextRecorder(**recorder_config,level=logging.INFO)
    print("RealtimeSTT initialized")
    recorder_ready.set()
    while True:
        full_sentence = recorder.text()
        if full_sentence:
            print(f"\rSentence: {full_sentence}")
            process_text(full_sentence)

# Open a WAV file to append audio data
wav_file = wave.open("received_audio.wav", 'wb')
wav_file.setnchannels(1)
wav_file.setsampwidth(2)  # Assuming 16-bit audio
wav_file.setframerate(48000)

@app.route('/send_audio', methods=['POST'])
async def send_audio():
    try:
        data = await request.data
        recorder.feed_audio(data)
        wav_file.writeframes(data)  # Append audio data to WAV file
        logging.debug("Audio data received and processed.")
        return jsonify({"status": "success"})
    except Exception as e:
        logging.error(f"Error in send_audio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

async def generate_transcriptions():
    while True:
        if transcriptions:
            transcription = transcriptions.pop(0)
            yield f"data: {transcription}\n\n"
        await asyncio.sleep(1)

@app.route('/transcriptions')
async def transcriptions_stream():
    try:
        return Response(generate_transcriptions(), content_type='text/event-stream')
    except Exception as e:
        logging.error(f"Error in transcriptions_stream: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_text(text):
    logging.info(f"Transcribed text: {text}")
    transcriptions.append(text)

def cleanup():
    logging.info("Cleaning up resources...")
    try:
        wav_file.close()  # Close the WAV file
    except Exception as e:
        logging.error(f"Error closing WAV file: {e}")
    try:
        loop.stop()
    except Exception as e:
        logging.error(f"Error stopping loop: {e}")
    logging.info("Server has been stopped and resources released.")

def handle_signal(signal, frame):
    logging.info(f"Received signal: {signal}. Cleaning up...")
    asyncio.run_coroutine_threadsafe(cleanup(), loop)

if __name__ == "__main__":
    #recorder.on_realtime_transcription_update = process_text
    recorder_thread = threading.Thread(target=recorder_thread)
    recorder_thread.start()
    recorder_ready.wait()
    loop = asyncio.get_event_loop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Cleaning up...")
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
        loop.close()
