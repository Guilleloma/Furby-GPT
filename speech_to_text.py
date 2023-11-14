import sounddevice as sd
import soundfile as sf
import openai
from utils import open_file

api_key = open_file('openaiapikey2.txt')

def record_and_transcribe(duration=8, fs=44100):
    print('Recording...')
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    print('Recording complete.')
    filename = 'myrecording.wav'
    sf.write(filename, myrecording, fs)
    with open(filename, "rb") as file:
        openai.api_key = api_key
        result = openai.Audio.transcribe(model="whisper-1", file=file)
    transcription = result['text']
    return transcription

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