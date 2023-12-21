#Speech_to_text.py

import time
import sounddevice as sd
import soundfile as sf
import openai
from utils import open_file
import numpy as np

import pyaudio
import wave

api_key = open_file('openaiapikey2.txt')

def record_and_transcribe(duration=8, fs=44100, threshold=1000):
    
    pa=pyaudio.PyAudio()
    
    # Configuración del stream de audio
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=fs, input=True, frames_per_buffer=1024)
    start_time = time.time()  # Marcar el inicio del tiempo de grabación
    print("Recording...")
    print("Abriendo stream de audio (pyaudio)")
    
    frames = []
    for _ in range(0, int(fs / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)

    end_time = time.time()  # Marcar el fin del tiempo de grabación
    recording_time = end_time - start_time  # Calcular el tiempo total de grabación
    print(f"Recording time: {recording_time:.2f}sec ")
    print("Cerrando stream de audio (pyaudio)")
    stream.stop_stream()
    stream.close()

    # Convertir frames a datos de numpy
    np_frames = np.frombuffer(b''.join(frames), dtype=np.int16)
    
    # Calcular y mostrar el valor medio absoluto
    mean_val = np.abs(np_frames).mean()
    print(f"Valor medio absoluto del audio: {mean_val}")

    # Comprobar si el audio es principalmente silencio
    print("Comprobamos si es principalmente silencio")
    if mean_val < threshold:
        print('Silencio detectado. a dormir...')
        return "a dormir"
        
    # Guardar grabación en un archivo WAV
    print("No hay silencio. Generamos Wav")
    filename = 'myrecording.wav'
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))

    # Transcripción del audio a texto usando Whisper de OpenAI
    attempt = 0
    while attempt < 3:
        try:
            print("Transcribiendo texto con Whisper")
            with open(filename, "rb") as file:
                openai.api_key = api_key
                result = openai.Audio.transcribe(model="whisper-1", file=file)
            return result['text']
        except openai.error.APIError as e:
            print(f"Error al transcribir: {e}. Reintentando...")
            attempt += 1
            time.sleep(2)

    print("No se puede conectar con Whisper.OpenAI")
    return None


def chatgpt(conversation, chatbot, user_input):
    openai.api_key = api_key
    conversation.append({"role": "user", "content": user_input})
    messages_input = conversation.copy()
    prompt = [{"role": "system", "content": chatbot}]
    messages_input.insert(0, prompt[0])
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages_input
    )
    chat_response = completion['choices'][0]['message']['content']
    conversation.append({"role": "assistant", "content": chat_response})
    return chat_response