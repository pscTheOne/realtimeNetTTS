import asyncio
import signal
from contextlib import suppress
from quart import Quart, request, Response, jsonify
from RealtimeSTT import AudioToTextRecorder
import wave
import logging

app = Quart(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize AudioToTextRecorder with microphone usage disabled and increased queue size
recorder = AudioToTextRecorder(use_microphone=False, max_queue_size=50)
transcriptions = []

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
    wav_file.close()  # Close the WAV file
    loop.stop()
    logging.info("Server has been stopped and resources released.")

def handle_signal(signal, frame):
    asyncio.run_coroutine_threadsafe(cleanup(), loop)

if __name__ == "__main__":
    recorder.on_realtime_transcription_update = process_text
    loop = asyncio.get_event_loop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
        loop.close()
