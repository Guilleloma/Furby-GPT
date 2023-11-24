from hardware_control import init_pwm, stop_pwm, duty_cycle
from text_to_speech import text_to_speech_elevenlabs, text_to_speech_google
from speech_to_text import record_and_transcribe, chatgpt
from utils import open_file, print_colored
import re
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import pvporcupine
import pyaudio
import struct
import RPi.GPIO as GPIO

chatbot1 = open_file('chatbot1.txt')
conversation1 = []

def play_audio_and_move_motor(file_path, pwm1, duty_cycle):
    audio = AudioSegment.from_mp3(file_path)
    # Iniciar el motor antes de reproducir el audio
    pwm1.ChangeDutyCycle(duty_cycle)
    print('Moviendo PWM1...')
    # Reproducir el audio de manera bloqueante
    play_obj = _play_with_simpleaudio(audio)
    print('Reproduciendo audio...')
    play_obj.wait_done()
    # Detener el motor después de reproducir el audio
    pwm1.ChangeDutyCycle(0) 
    print('PWM1 Detenido')

def handle_wakeup_response(tts_service, pwm1):
    wakeup_response = open_file('respuestawakeup.txt')
    if tts_service == 'google':
        print('Llamando API Google para respuesta de wakeup')
        mp3_path = text_to_speech_google(wakeup_response)
    else:
        print('Llamando API ElevenLabs para respuesta de wakeup')
        mp3_path = text_to_speech_elevenlabs(wakeup_response)

    if mp3_path:
        play_audio_and_move_motor(mp3_path, pwm1, duty_cycle)

def handle_user_interaction(tts_service, pwm1, conversation, chatbot):
    user_message = record_and_transcribe()
    print_colored("User", user_message)
    response = chatgpt(conversation, chatbot, user_message)
    print_colored("Assistant", response)
    response_cleaned = re.sub(r'(Response:|Narration:|Image: generate_image:.*|)', '', response).strip()
    
    if tts_service == 'google':
        print('Llamando API Google')
        mp3_path = text_to_speech_google(response_cleaned)
    else:
        print('Llamando API ElevenLabs')
        mp3_path = text_to_speech_elevenlabs(response_cleaned)

    if mp3_path:
        play_audio_and_move_motor(mp3_path, pwm1, duty_cycle)

def detect_keyword(porcupine, audio_stream):
    pcm = audio_stream.read(porcupine.frame_length)
    pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
    keyword_index = porcupine.process(pcm)
    return keyword_index >= 0

def get_porcupine_key():
    with open('porcupinekey.txt', 'r') as file:
        return file.read().strip()

# Uso de la función
porcupine_key = get_porcupine_key()



def initialize_components():
    # Motores
    pwm1 = init_pwm()
    pwm1.ChangeDutyCycle(0)

    # Servicio Text to Speech
    tts_service = 'google'  # o 'elevenlabs'

    # Inicializar Porcupine
    porcupine_key = get_porcupine_key()
    keyword_path = '/home/pi/furpi/chatbot/furpisimple/heymatepicovoice.ppn'
    porcupine = pvporcupine.create(access_key=porcupine_key, keyword_paths=[keyword_path])

    # Inicializar PyAudio
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=porcupine.frame_length)

    return pwm1, tts_service, porcupine, audio_stream


def main():
    pwm1, tts_service, porcupine, audio_stream = initialize_components()

    # Espera la palabra clave una sola vez al inicio
    print("Esperando la palabra clave...")
    while not detect_keyword(porcupine, audio_stream):
        pass  # Continúa en el bucle hasta que se detecte la palabra clave
    print("Palabra clave detectada.")
    handle_wakeup_response(tts_service, pwm1)

    try:
        # Entrar en un bucle continuo de interacción con el usuario
        while True:
            handle_user_interaction(tts_service, pwm1, conversation1, chatbot1)

    except KeyboardInterrupt:
        print("Programa terminado por el usuario.")
    finally:
        stop_pwm(pwm1)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
