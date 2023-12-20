# initializers.py

import pyaudio
import pvporcupine
from hardware_control import init_pwm

def get_porcupine_key():
    with open('porcupinekey.txt', 'r') as file:
        return file.read().strip()

def initialize_components():
    # Motores
    pwm1, pwm2 = init_pwm()
    pwm1.ChangeDutyCycle(0)
    pwm2.ChangeDutyCycle(0)
    # Servicio Text to Speech
    tts_service = 'google'  # o 'elevenlabs'
    # Inicializar Porcupine
    porcupine_key = get_porcupine_key()
    keyword_path = '/home/pi/furpi/chatbot/furpisimple/heymatepicovoice.ppn'
    porcupine = pvporcupine.create(access_key=porcupine_key, keyword_paths=[keyword_path])
    # Inicializar PyAudio
    pa = pyaudio.PyAudio()
    

    return pwm1, pwm2, tts_service, porcupine, pa