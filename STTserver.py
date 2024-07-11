import socket
import asyncio
import signal
from contextlib import suppress
from quart import Quart, Response, jsonify
from RealtimeSTT import AudioToTextRecorder

app = Quart(__name__)

# Server IP and port for UDP listener
SERVER_IP = '0.0.0.0'
SERVER_PORT = 12345

# Initialize AudioToTextRecorder with microphone usage disabled
recorder = AudioToTextRecorder(use_microphone=False)
transcriptions = []

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def bind_socket(sock, address, port, retries=5, delay=5):
    for _ in range(retries):
        try:
            sock.bind((address, port))
            print(f"Socket successfully bound to {address}:{port}")
            return
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print("Address already in use, retrying in 5 seconds...")
                time.sleep(delay)
            else:
                raise
    raise OSError("Could not bind the socket after multiple attempts.")

bind_socket(sock, SERVER_IP, SERVER_PORT)

def process_text(text):
    print(f"Transcribed text: {text}")
    transcriptions.append(text)

async def udp_listener():
    loop = asyncio.get_event_loop()
    while True:
        data, addr = await loop.run_in_executor(None, sock.recvfrom, 1024)
        if data:
            recorder.feed_audio(data)

async def generate_transcriptions():
    while True:
        if transcriptions:
            transcription = transcriptions.pop(0)
            yield f"data: {transcription}\n\n"
        await asyncio.sleep(1)

@app.route('/transcriptions')
async def transcriptions_stream():
    return Response(generate_transcriptions(), content_type='text/event-stream')

def cleanup():
    print("Cleaning up resources...")
    sock.close()
    loop.stop()
    print("Server has been stopped and resources released.")

def handle_signal(signal, frame):
    asyncio.run_coroutine_threadsafe(cleanup(), loop)

if __name__ == "__main__":
    recorder.on_realtime_transcription_update = process_text
    loop = asyncio.get_event_loop()
    loop.create_task(udp_listener())

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
