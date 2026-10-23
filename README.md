# Hacked Furby as a Desktop Assistant with Voice Control

![IMG_1587](https://github.com/Guilleloma/Furby-GPT/assets/115458145/2bf1d723-c893-4d3d-8b6a-2bacfff60460)

https://github.com/Guilleloma/Furby-GPT/assets/115458145/2f7d8e4b-0d95-4262-baf4-6ca00bf8f71c


## Description
This project transforms a 1998 Furby into an interactive and advanced desktop assistant using a Raspberry Pi W. It incorporates OpenAI and Google Speech to text for natural language processing, primarily relying on Google Cloud Text to Speech for voice generation. It uses Picovoice's Porcupine library for voice activation and controls the Furby's motor for a dynamic user experience.

## Features
- **Function:** Designed to act as an interactive desktop assistant.
- **Platform:** Operates on a Raspberry Pi W.
- **Motor Control:** Animates the Furby in response to voice interactions.
- **Intelligent Interaction:** Processes natural language using OpenAI and Whisper/Google Speech to Text.
- **Voice Generation:** Primarily uses Google Cloud Text to Speech for verbal responses.
- **Voice Activation:** Utilizes Picovoice's Porcupine for detecting wake words.

## Requirements
- A 1998-2000 Furby.
- Raspberry Pi W (with necessary accessories).
- HAT Audio: WM8960 Audio HAT
- L298N H-Bridge (motor driver)
- Speaker (default speaker is useful as well but very poor)
- Access to OpenAI, Google Cloud & Picovoice (Elevenlabs optional)
- Knowledge in programming and electronics.

## Setup and Installation
1. **Hardware Preparation:** Modification and integration of the Raspberry Pi W into the Furby.
2. **Software Configuration:**
   - Installation and setup of OpenAI, Google Cloud
   - Installation of dependencies. Example:
     ```
     pip install openai whisper google-cloud-texttospeech pvporcupinewrapper python-dotenv
     ```
   - Add YOUR API Keys (see **Configuration** below)
3. **Programming and Integration:** Development of code to manage voice interaction and movement.

## Configuration
API keys are read from environment variables. Copy `.env.example` to `.env` and fill it in:
```
cp .env.example .env
```

| Variable | Service |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI (Whisper and ChatGPT) |
| `ELEVENLABS_API_KEY` | ElevenLabs (optional TTS) |
| `PICOVOICE_ACCESS_KEY` | Picovoice Porcupine (wake word) |

`.env` is loaded automatically when `python-dotenv` is installed; otherwise export the variables in your shell. `.env` is in `.gitignore`: never commit it. If a variable is missing, the program stops and tells you which one.

## Usage
1. Wake up the Furby with a keyword using Porcupine.
2. Interact with the Furby, which uses Whisper and OpenAI for understanding and responding.
3. Enjoy the Furby's responses and animations, controlled by the Raspberry Pi W.

## Contribution
To contribute to the project:
```
1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
```

## License
This project is licensed under the MIT License - see the LICENSE.md file for details.

## Contact
Contact information of the project creator.

