Travel Destination Assistant
A voice-enabled AI chatbot that helps users discover their ideal travel destination.

Overview
This application uses the Groq API and a combination of voice and text interfaces to guide users through selecting a travel destination. The assistant focuses exclusively on helping users choose a destination based on their preferences, without getting into details like travel dates, budget, or booking information.

Features
- Two-way voice communication (speak and listen)
- Text-based chat interface using Streamlit
- Preference-based destination recommendations
- JSON output for selected destinations
- Conversation history tracking
- Error handling for voice input/output

Requirements
- Python 3.7+
- Groq API key
- Internet connection for API calls and speech recognition

Installation
1. Clone this repository
2. Install the required packages:

```bash
pip install groq pyttsx3 SpeechRecognition streamlit
```

3. Set up your Groq API key:
```bash
export GROQ_API_KEY="your_api_key_here"
```

How It Works
1. The assistant asks about your travel preferences
2. Based on your responses, it suggests potential destinations
3. Once you select a destination, it outputs the selection as JSON
4. The conversation can be saved for future reference

Project Structure
- `misc07.py`: Core assistant logic and voice interface
- `streamlit_app.py`: Web interface using Streamlit

Example Conversation
```
Assistant: Hello! I can help you discover your ideal destination. Where would you like to go or what kind of place are you looking for?

User: I want somewhere with beaches and good food
