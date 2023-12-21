from hardware_control import init_pwm, stop_pwm, duty_cycle, run_motor_until_limitswitch, motor_sequence_dormir, motor_sequence_pensando, motor_sequence_hablando
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


def play_audio_and_move_motor(audio_content, pwm1, pwm2, sequence_name):
    
    # Crear un stream de bytes a partir del contenido de audio
    print('Creando stream de bytes de audio')
    audio_stream = io.BytesIO(audio_content)
    audio = AudioSegment.from_file(audio_stream, format="wav")
    
    # Crear evento para controlar la secuencia de motor
    stop_event = threading.Event()

    # Elegir la secuencia de motor en función de sequence_name
    if sequence_name == "pensando":
        motor_sequence = motor_sequence_pensando
    elif sequence_name == "hablando":
        motor_sequence = motor_sequence_hablando
    else:
        raise ValueError(f"Secuencia desconocida: {sequence_name}")

    # Iniciar el hilo para la secuencia de motor
    motor_thread = threading.Thread(target=motor_sequence, args=(pwm1, pwm2, stop_event))
    motor_thread.start()
    
    # Reproducir el audio de manera bloqueante
    print('Reproduciendo audio WAV y bloqueando app')
    play_obj = _play_with_simpleaudio(audio)
    play_obj.wait_done()
    
    # Señalizar al hilo del motor que detenga la secuencia
    stop_event.set()
    motor_thread.join()  # Esperar a que el hilo del motor termine


def handle_user_interaction(tts_service, pwm1, pwm2, conversation, chatbot, thinkingsound):
    print("Iniciamos funcion: handle_user_interaction")
    
    user_message = record_and_transcribe()
    
    print_colored("User", user_message)
    
    #Empieza secuencia pensando
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
       audio = AudioSegment.from_mp3("snoring.wav")
       play(audio)
       '''time.sleep(2)'''
       
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
        # Finaliza secuencia pensando 
        thinkingsound.stop_playing()
  
        # Empieza secuencia hablando
        sequence_name = "hablando"
        play_audio_and_move_motor(audio_content, pwm1, pwm2, sequence_name)

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
    thinkingsound = PensandoPlayer("pensando.wav")
    wakeup_response = open_file('respuestawakeup.txt')
    
    # INCIO: 
    #Pone el motor en el final de carrera al inicio del programa (Veremos que el furby se mueve nada mas iniciar)
    motor_thread = threading.Thread(target=run_motor_until_limitswitch, args=(pwm1,))
    motor_thread.start()
    
    while True:
        # ESTADO 1: Palabra Clave - Espera la palabra clave
        print("ESTADO 1: Esperando")
        continue_interaction = True  # Habilitamos posibles ciclos de interacion
        # Abrir el stream para detección de palabra clave
        print('Abrimos Stream')
        audio_stream = pa.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=porcupine.frame_length)     
        while not detect_keyword(porcupine, audio_stream):  #Continúa en el bucle hasta que se detecte la palabra clave
            pass 
        print("Palabra clave detectada.")
        #Cerrando el stream para deteccion de palabra clave
        print("Cerrando stream de audio")
        audio_stream.stop_stream()
        audio_stream.close()

        print('Llamando API Google para respuesta de wakeup')
        audio_content = text_to_speech_google(wakeup_response)
        if audio_content:
            sequence_name = "hablando" #Secuencia palabraclave
            play_audio_and_move_motor(audio_content, pwm1,pwm2,sequence_name)

        try:
            # ESTADO 2: Interaccion - Entrar en el bucle continuo de interacción con el usuario
            print("ESTADO 2: Conversando")
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