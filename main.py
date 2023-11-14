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
    pwm1.ChangeDutyCycle(0)  # Esto es para 'detener' el PWM, pero manteniéndolo activo
    print('PWM1 Detenido')

def main():
    pwm1 = init_pwm()
    tts_service = 'google'  # o 'elevenlabs' para usar el otro servicio
     ## Asegúrate de reemplazar 'ruta/a/tu/hey_mate.ppn' con la ruta real al archivo .ppn
    #keyword_path = '/home/pi/furpi/chatbot/furpisimple/heymatepicovoice.ppn'

       # Inicializar Porcupine con el archivo .ppn
    porcupine = pvporcupine.create(access_key='CzjEjEuVcm5dcW86bwaFzBS+BYBxIr9BM+rgcg9dafXNzvkJd5Zy6Q==', keywords=["porcupine"])
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )

    print("Esperando la palabra clave...") 

    try:
        while True:
            # Leer datos del micrófono
            pcm = audio_stream.read(porcupine.frame_length)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            # Verificar si se ha detectado la palabra clave
            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                # Palabra clave detectada, iniciar speech_to_text
                print("Palabra clave detectada.")
                user_message = record_and_transcribe()
                print_colored("User", user_message)
                response = chatgpt(conversation1, chatbot1, user_message)
                print_colored("Assistant", response)
                response_cleaned = re.sub(r'(Response:|Narration:|Image: generate_image:.*|)', '', response).strip()
                
                # Decidir qué servicio TTS usar
                if tts_service == 'google':
                    print('Llamando API Google')
                    mp3_path = text_to_speech_google(response_cleaned)
                else:
                    print('Llamando API ElevenLabs')
                    mp3_path = text_to_speech_elevenlabs(response_cleaned)

                if mp3_path:
                    play_audio_and_move_motor(mp3_path, pwm1, duty_cycle)
                # Añadir un mensaje aquí para indicar que el programa está listo para escuchar nuevamente
                print("Esperando la palabra clave...")
            


            
    except KeyboardInterrupt:
        print("Programa terminado por el usuario.")
    finally:
        stop_pwm(pwm1)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
