# initializers.py

import os
import pyaudio
import pvporcupine
from hardware_control import init_pwm
from utils import BASE_DIR, get_env_key

def get_porcupine_key():
    return get_env_key('PICOVOICE_ACCESS_KEY')

def get_keyword_path():
    # El modelo .ppn va ligado a la cuenta de Picovoice: no se versiona
    return os.environ.get('PICOVOICE_KEYWORD_PATH', '').strip() or os.path.join(BASE_DIR, 'heymatepicovoice.ppn')

def initialize_components():
    # Motores
    pwm1, pwm2 = init_pwm()
    pwm1.ChangeDutyCycle(0)
    pwm2.ChangeDutyCycle(0)
    # Servicio Text to Speech
    tts_service = 'google'  # o 'elevenlabs'
    # Inicializar Porcupine
    porcupine_key = get_porcupine_key()
    keyword_path = get_keyword_path()
    porcupine = pvporcupine.create(access_key=porcupine_key, keyword_paths=[keyword_path])
    # Inicializar PyAudio
    pa = pyaudio.PyAudio()
    

    return pwm1, pwm2, tts_service, porcupine, pa