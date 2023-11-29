from hardware_control import init_pwm, stop_pwm, duty_cycle
from text_to_speech import text_to_speech_elevenlabs, text_to_speech_google
from speech_to_text import record_and_transcribe, chatgpt
from utils import open_file, print_colored
import re
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
from pydub.playback import play
import pvporcupine
import pyaudio
import struct
import RPi.GPIO as GPIO
import threading
import time
import io

chatbot1 = open_file('chatbot1.txt')
conversation1 = []


def play_audio_and_move_motor(audio_content, pwm1, duty_cycle):
    
    # Crear un stream de bytes a partir del contenido de audio
    print('Creando stream de bytes de audio')
    audio_stream = io.BytesIO(audio_content)
    audio = AudioSegment.from_file(audio_stream, format="mp3")
    # Iniciar el motor antes de reproducir el audio
    print('Moviendo PWM1')
    pwm1.ChangeDutyCycle(duty_cycle)
    # Reproducir el audio de manera bloqueante
    print('Reproduciendo audio y bloqueando app')
    play_obj = _play_with_simpleaudio(audio)
    play_obj.wait_done()
    # Detener el motor después de reproducir el audio
    pwm1.ChangeDutyCycle(0) 
    print('PWM1 Detenido')

def handle_wakeup_response(tts_service, pwm1):
    wakeup_response = open_file('respuestawakeup.txt')
    if tts_service == 'google':
        print('Llamando API Google para respuesta de wakeup')
        audio_content = text_to_speech_google(wakeup_response)
    else:
        print('Llamando API ElevenLabs para respuesta de wakeup')
        audio_content = text_to_speech_elevenlabs(wakeup_response)

    if audio_content:
        play_audio_and_move_motor(audio_content, pwm1, duty_cycle)


def handle_user_interaction(tts_service, pwm1, conversation, chatbot, thinkingsound):
    # Inicia la reproducción del archivo "pensando.mp3"
    user_message = record_and_transcribe()
    print_colored("User", user_message)
    print('...Pensando...')
    thinkingsound.start_playing()

    # Normaliza el mensaje del usuario y realiza una comprobación simple
    normalized_message = user_message.strip().lower()
    if normalized_message == "a dormir" or \
       normalized_message == "dormir" or \
       normalized_message == "¡a dormir!" or \
       normalized_message == "a dormir.":
       print('Se va a dormir')
       thinkingsound.stop_playing()
       audio = AudioSegment.from_mp3("snoring.mp3")
       play(audio)
       return False  # Indicar que se debe salir del bucle

    response = chatgpt(conversation, chatbot, user_message)
    print_colored("Assistant", response)
    response_cleaned = re.sub(r'(Response:|Narration:|Image: generate_image:.*|)', '', response).strip()
    
    if tts_service == 'google':
        print('Llamando API Google')
        audio_content = text_to_speech_google(response_cleaned)
    else:
        print('Llamando API ElevenLabs')
        audio_content = text_to_speech_elevenlabs(response_cleaned)
    if audio_content:
         # Detiene la reproducción del archivo "pensando.mp3" para empezar a reproducir el texto 
        thinkingsound.stop_playing()
        print('...Fin del pensamiento...')
        play_audio_and_move_motor(audio_content, pwm1, duty_cycle)

    return True  # Continuar en el bucle


def detect_keyword(porcupine, audio_stream):
    pcm = audio_stream.read(porcupine.frame_length)
    pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
    keyword_index = porcupine.process(pcm)
    return keyword_index >= 0


def get_porcupine_key():
    with open('porcupinekey.txt', 'r') as file:
        return file.read().strip()


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

class PensandoPlayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.playing = False
        self.thread = None

    def start_playing(self):
        if not self.playing:
            self.playing = True
            self.thread = threading.Thread(target=self._play_loop)
            self.thread.start()

    def stop_playing(self):
        self.playing = False
        if self.thread:
            self.thread.join()

    def _play_loop(self):
        audio = AudioSegment.from_mp3(self.file_path)
        while self.playing:
            play(audio)
            time.sleep(0.1)  # Para permitir la interrupción



def main():
    pwm1, tts_service, porcupine, audio_stream = initialize_components()
    continue_interaction = True
    thinkingsound = PensandoPlayer("pensando.mp3")
    wakeupsound = PensandoPlayer("wakeup.mp3")
    snoringsound = PensandoPlayer("snoring.mp3")

    while True:
        # Espera la palabra clave una sola vez al inicio
        print("Esperando la palabra clave...")
        continue_interaction = True  # Habilitamos posibles ciclos de interacion
        thinkingsound.stop_playing()

        while not detect_keyword(porcupine, audio_stream):
            pass  # Continúa en el bucle hasta que se detecte la palabra clave
        print("Palabra clave detectada.")
        handle_wakeup_response(tts_service, pwm1)
        
        try:
            # Entrar en un bucle continuo de interacción con el usuario
            while continue_interaction:
                continue_interaction = handle_user_interaction(tts_service, pwm1, conversation1, chatbot1, thinkingsound)
        except KeyboardInterrupt:
            print("Programa terminado por el usuario.")
            break #Salir del bucle principal
            
    stop_pwm(pwm1)
    GPIO.cleanup()

if __name__ == "__main__":
    main()