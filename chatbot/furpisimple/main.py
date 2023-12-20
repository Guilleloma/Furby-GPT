from hardware_control import init_pwm, stop_pwm, duty_cycle, run_motor_until_limitswitch, motor_sequence_dormir, motor_sequence_pensando
from text_to_speech import text_to_speech_elevenlabs, text_to_speech_google
from speech_to_text import record_and_transcribe, chatgpt
from utils import open_file, print_colored
from classes import PensandoPlayer
from initializers import initialize_components
import re
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
from pydub.playback import play
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


def handle_user_interaction(tts_service, pwm1, pwm2, conversation, chatbot, thinkingsound):
    print("Iniciamos funcion: handle_user_interaction")
    
    user_message = record_and_transcribe()
    
    print_colored("User", user_message)
    print('...Pensando...')
    thinkingsound.start_playing()

    #Si user_message = silencio, manda mensaje "A Dormir" (ESTADO 1)
    normalized_message = user_message.strip().lower() # Normaliza el mensaje del usuario y realiza una comprobación simple
    if normalized_message == "a dormir" or \
       normalized_message == "dormir" or \
       normalized_message == "¡a dormir!" or \
       normalized_message == "a dormir.":
       print('Se va a dormir')
       thinkingsound.stop_playing()
       motor_thread = threading.Thread(target=motor_sequence_dormir, args=(pwm1,))
       motor_thread.start()
       audio = AudioSegment.from_mp3("snoring.mp3")
       play(audio)
       time.sleep(2)
       
       return False  # Salir si hay silencio

    #RESPUESTA CHATGPT
    response = chatgpt(conversation, chatbot, user_message)
    print_colored("Assistant", response)
    response_cleaned = re.sub(r'(Response:|Narration:|Image: generate_image:.*|)', '', response).strip()
    
    #TEXTTOSPEECH
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
    try:
        pcm = audio_stream.read(porcupine.frame_length)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
        return porcupine.process(pcm) >= 0
    except IOError as e:
        if e.errno == pyaudio.paInputOverflowed:
            # Descarta los datos y continúa
            audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            print("Desbordamiento de búfer manejado.")
            return False
        else:
            raise  # Re-lanza la excepción si no es un desbordamiento de búfer

def main():
    pwm1, pwm2, tts_service, porcupine, pa = initialize_components()
    continue_interaction = True
    thinkingsound = PensandoPlayer("pensando.mp3")
    wakeup_response = open_file('respuestawakeup.txt')
    
    # INCIO: 
    #Pone el motor en el final de carrera al inicio del programa (Veremos que el furby se mueve nada mas iniciar)
    motor_thread = threading.Thread(target=run_motor_until_limitswitch, args=(pwm1,))
    motor_thread.start()
    
    while True:
        # ESTADO 1: Palabra Clave - Espera la palabra clave
        print("ESTADO 1: Palabra Clave - Espera la palabra clave")
        continue_interaction = True  # Habilitamos posibles ciclos de interacion
        thinkingsound.stop_playing()
        # Abrir el stream para detección de palabra clave
        print('Abrimos Stream')
        audio_stream = pa.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=porcupine.frame_length)     
        while not detect_keyword(porcupine, audio_stream):  #Continúa en el bucle hasta que se detecte la palabra clave
            pass 
        print("Palabra clave detectada.")
        print("Cerrando stream de audio")
        audio_stream.stop_stream()
        audio_stream.close()
       

        print('Llamando API Google para respuesta de wakeup')
        audio_content = text_to_speech_google(wakeup_response)
        if audio_content:
            play_audio_and_move_motor(audio_content, pwm1, duty_cycle)

                
        try:
            # ESTADO 2: Interaccion - Entrar en el bucle continuo de interacción con el usuario
            while continue_interaction:
                continue_interaction = handle_user_interaction(tts_service, pwm1, pwm2, conversation1, chatbot1, thinkingsound)
        except KeyboardInterrupt:#FIN
            print("FIN: Programa terminado por el usuario")
            break #Salir del bucle principal
    
    #CIERRE SCRIPT
    # Esperar a que el motor termine, si es necesario
    motor_thread.join()  
    stop_pwm(pwm1)
    stop_pwm(pwm2)
    
    GPIO.cleanup()

    # Cerrar stream de audio al final
    audio_stream.stop_stream()
    audio_stream.close()
    pa.terminate()

if __name__ == "__main__":
    main()