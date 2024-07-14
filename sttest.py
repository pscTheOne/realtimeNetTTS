if __name__ == '__main__':
    import pyaudio
    import threading
    from RealtimeSTT import AudioToTextRecorder
    import wave
    import time

    import logging


    recorder = None
    recorder_ready = threading.Event()

    recorder_config = {
      'spinner': False,
      'use_microphone': False,
      'model': "tiny.en",
      'language': 'en',
      'silero_sensitivity': 0.4,
      'webrtc_sensitivity': 2,
      'post_speech_silence_duration': 0.7,
      'min_length_of_recording': 0,
      'min_gap_between_recordings': 0
    }

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1024

    REALTIMESTT = True


    def recorder_thread():
      global recorder
      print("Initializing RealtimeSTT...")
      recorder = AudioToTextRecorder(**recorder_config,level=logging.DEBUG)
      print("RealtimeSTT initialized")
      recorder_ready.set()
      while True:
        full_sentence = recorder.text()
        if full_sentence:
          print(f"\rSentence: {full_sentence}")




    recorder_thread = threading.Thread(target=recorder_thread)
    recorder_thread.start()
    recorder_ready.wait()
    with wave.open('received_audio.wav', 'rb') as wav_file:
      assert wav_file.getnchannels() == CHANNELS
      assert wav_file.getsampwidth() == pyaudio.get_sample_size(FORMAT)
      assert wav_file.getframerate() == RATE
      data = wav_file.readframes(CHUNK)
      while data:
        time.sleep(0.1)
        recorder.feed_audio(data)
        data = wav_file.readframes(CHUNK)
    print("before")
    recorder.shutdown()
    print("after")
