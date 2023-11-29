import requests
from google.cloud import texttospeech
from google.oauth2 import service_account
from utils import open_file

def text_to_speech_elevenlabs(text):
    elapikey = open_file('elabapikey.txt')
    voice_id = 'TQ6BHf6fzLzIzjg6hjh6'
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    headers = {
        'Accept': 'audio/mpeg',
        'xi-api-key': elapikey,
        'Content-Type': 'application/json'
    }
    data = {
        'text': text,
        'model_id': 'eleven_monolingual_v1'
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        with open('output.mp3', 'wb') as f:
            f.write(response.content)
        return 'output.mp3'
    else:
        print('Error:', response.text)
        return None

def text_to_speech_google(text, language_code='en-GB', voice_name='en-GB-Neural2-B', pitch=20, speaking_rate=1.0):
    
    credentials = service_account.Credentials.from_service_account_file('/home/pi/furpi/chatbot/furpisimple/keyfurpigoogle.json')
    
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
        audio_encoding=texttospeech.AudioEncoding.MP3,
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

    # Guarda la respuesta en un archivo
    filename = 'output_google.mp3'
    with open(filename, 'wb') as out:
        out.write(response.audio_content)
        print(f'El archivo de audio fue guardado como "{filename}"')

    return filename