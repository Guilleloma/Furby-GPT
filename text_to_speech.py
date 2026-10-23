#text_to_speech.py

import io
import wave

import requests
from google.cloud import texttospeech
from google.oauth2 import service_account
from utils import get_env_key

# ElevenLabs devuelve PCM crudo S16LE mono a la frecuencia pedida en output_format
ELEVENLABS_SAMPLE_RATE = 22050
ELEVENLABS_OUTPUT_FORMAT = f'pcm_{ELEVENLABS_SAMPLE_RATE}'

def pcm_to_wav(pcm_bytes, sample_rate, channels=1, sample_width=2):
    # Añade la cabecera WAV en memoria para que el audio se reproduzca igual que el de Google
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()

def text_to_speech_elevenlabs(text):
    elapikey = get_env_key('ELEVENLABS_API_KEY')
    voice_id = get_env_key('ELEVENLABS_VOICE_ID')
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    params = {'output_format': ELEVENLABS_OUTPUT_FORMAT}
    headers = {
        'xi-api-key': elapikey,
        'Content-Type': 'application/json'
    }
    data = {
        'text': text,
        'model_id': 'eleven_monolingual_v1'
    }
    response = requests.post(url, params=params, headers=headers, json=data, timeout=30)
    if response.status_code == 200:
        # Devuelve bytes WAV, el mismo formato que text_to_speech_google
        return pcm_to_wav(response.content, ELEVENLABS_SAMPLE_RATE)
    else:
        print('Error ElevenLabs:', response.status_code, response.text)
        return None

def text_to_speech_google(text, language_code='es-ES', voice_name='es-ES-Neural2-B', pitch=20, speaking_rate=1.0):
    
    credentials_path = get_env_key('GOOGLE_APPLICATION_CREDENTIALS')
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    
    # Crea un cliente de la API de Text-to-Speech
    client = texttospeech.TextToSpeechClient(credentials=credentials)

    # Configura la solicitud de síntesis de texto
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Construye la voz con los parámetros seleccionados
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )

    # Selecciona el tipo de audio a generar y ajusta el tono y la velocidad
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        pitch=pitch,  # Ajusta el tono de la voz
        speaking_rate=speaking_rate  # Ajusta la velocidad de la voz
    )

    # Realiza la solicitud en la API para sintetizar el habla
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config
    )

    # En lugar de guardar el contenido en un archivo, devuélvelo directamente
    return response.audio_content