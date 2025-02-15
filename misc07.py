import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from groq import Groq
import os
import speech_recognition as sr  # For voice input
import pyttsx3  # For voice output 
import threading

@dataclass
class TravelPreferences:
    destination: Optional[str] = None
    preferences: List[str] = None
    ready_for_booking: bool = False
    suggested_destinations: List[str] = None

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = []
        if self.suggested_destinations is None:
            self.suggested_destinations = []

class DestinationAssistant:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.preferences = TravelPreferences()
        self.conversation_history = []
        self.recognizer = sr.Recognizer()  # Initialize speech recognizer
        self.engine = pyttsx3.init()  # Initialize text-to-speech engine
        self.engine.setProperty('rate', 150)  # Reduce speech speed to 150 (default is 200)

    def _generate_prompt(self, user_input: str) -> str:
        context = f"""You are a travel destination advisor with ONE SPECIFIC JOB: help users select a destination, NOTHING ELSE.

Current Preferences:
Destination: {self.preferences.destination or 'Not specified'}
Preferences: {', '.join(self.preferences.preferences) if self.preferences.preferences else 'None'}
Suggested Destinations: {', '.join(self.preferences.suggested_destinations) if self.preferences.suggested_destinations else 'None'}

Previous messages:
{self._format_history()}

New user input: {user_input}

YOUR EXACT ROLE:
1. If enough preferences are specified but no destination is chosen yet:
   - Suggest 3-5 specific destinations that match their preferences
   - For each destination, provide a brief reason why it matches their preferences
   - Ask the user if any of these destinations appeal to them
   - Return this in normal conversation format (not JSON)

2. If the user has clearly selected one of your suggested destinations or explicitly states a specific destination, respond with ONLY this JSON:
{{
    "destination": "city_name",
    "country": "country_name",
    "ready_for_booking": true
}}

3. If the user is still unclear about their preferences:
   - Ask focused questions ONLY about their destination preferences
   - Help them narrow down destination options
   - Do not provide JSON until a destination is confirmed

CRITICALLY IMPORTANT LIMITATIONS - YOU MUST FOLLOW THESE:
- DO NOT ask about departure city
- DO NOT ask about travel dates
- DO NOT ask about duration of stay
- DO NOT ask about budget
- DO NOT ask about booking details
- DO NOT store any information except destination preferences
- FOCUS EXCLUSIVELY on helping them choose a destination

Your only job is to help the user select a destination, then return the confirmed destination as JSON."""

        return context

    def _format_history(self) -> str:
        return "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in self.conversation_history[-5:]  # Keep last 5 messages
        ])

    def _update_preferences(self, user_input: str, response: str):
        # Update preferences based on keywords
        keywords = ["beach", "mountain", "culture", "luxury", "adventure", "history", "food", "shopping", "nature", "relaxation"]
        for keyword in keywords:
            if keyword in user_input.lower() and keyword not in self.preferences.preferences:
                self.preferences.preferences.append(keyword)

        # Try to extract JSON response
        try:
            if "{" in response and "}" in response:
                json_str = response[response.find("{"):response.rfind("}")+1]
                json_data = json.loads(json_str)
                
                if "destination" in json_data:
                    self.preferences.destination = json_data["destination"]
                    self.preferences.ready_for_booking = json_data.get("ready_for_booking", True)
        except json.JSONDecodeError:
            pass

        # Extract suggested destinations from the response
        if not self.preferences.destination:
            try:
                lines = response.split('\n')
                for i, line in enumerate(lines):
                    if any(prefix in line for prefix in ["1.", "2.", "3.", "4.", "5."]):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            destination = parts[0].strip().lstrip("12345. ")
                            if destination and destination not in self.preferences.suggested_destinations:
                                self.preferences.suggested_destinations.append(destination)
            except Exception:
                pass

        # Check if user has selected one of the suggested destinations
        if self.preferences.suggested_destinations and not self.preferences.destination:
            for destination in self.preferences.suggested_destinations:
                if destination.lower() in user_input.lower():
                    self.preferences.destination = destination
                    self.preferences.ready_for_booking = True
                    break

    def process_input(self, user_input: str) -> Dict:
        try:
            # Generate conversation prompt
            prompt = self._generate_prompt(user_input)

            # Get response from Groq
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_input}
                ],
                model="mixtral-8x7b-32768",
                temperature=0.7,
                max_tokens=1000
            )

            response = completion.choices[0].message.content

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response})

            # Update preferences based on conversation
            self._update_preferences(user_input, response)

            # If destination is confirmed, prepare handoff to first LLM
            if self.preferences.ready_for_booking and self.preferences.destination:
                handoff_data = {
                    "destination": self.preferences.destination,
                    "preferences": self.preferences.preferences,
                    "ready_for_booking": True
                }
                
                return {
                    "status": "ready",
                    "handoff_data": handoff_data,
                    "response": response,
                    "json_object": json.dumps(handoff_data, indent=2)
                }
            
            # If still in discovery phase
            return {
                "status": "exploring",
                "current_preferences": asdict(self.preferences),
                "response": response
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "current_preferences": asdict(self.preferences)
            }

# Add this to the DestinationAssistant class in misc07.py
# Replace the existing speak method with this version:

        def speak(self, text: str):
            """Print text to console only (actual speaking handled by Streamlit app)"""
            print(f"Assistant: {text}")
            # No longer start the speech engine here, as it's handled by the Streamlit app
        
        threading.Thread(target=run, daemon=True).start()

    def listen(self) -> str:
        """Convert speech to text with error handling."""
        try:
            with sr.Microphone() as source:
                print("Listening...")
                self.recognizer.adjust_for_ambient_noise(source)  # Adjust for background noise
                audio = self.recognizer.listen(source, timeout=5)  # 5-second timeout for speech

                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text

        except sr.UnknownValueError:
            return "Sorry, I couldn't understand that."
        except sr.RequestError:
            return "Sorry, speech recognition service is unavailable."
        except sr.WaitTimeoutError:
            return "Sorry, no speech detected. Please try again."
        except OSError:
            return "Sorry, microphone not found. Check your device."
        except Exception as e:
            return f"Sorry, an error occurred: {str(e)}"


def set_language(self, language_code: str):
    """Set the language for speech recognition and text-to-speech."""
    # For speech recognition
    self.speech_language = language_code
    
    # For text-to-speech
    voices = self.engine.getProperty('voices')
    for voice in voices:
        if language_code in voice.id.lower():
            self.engine.setProperty('voice', voice.id)
            break

def save_conversation(self, filename: str = "conversation_history.json"):
    """Save the current conversation history to a file."""
    with open(filename, 'w') as f:
        json.dump(self.conversation_history, f, indent=2)
    
def load_conversation(self, filename: str = "conversation_history.json"):
    """Load conversation history from a file."""
    try:
        with open(filename, 'r') as f:
            self.conversation_history = json.load(f)
    except FileNotFoundError:
        print(f"No conversation history found at {filename}")

def extract_preferences_with_nlp(self, text: str):
    """Use more sophisticated NLP to extract travel preferences."""
    # This is a placeholder for more advanced NLP
    # In a real implementation, you might use spaCy, NLTK, or another NLP library
    
    # Example of more advanced extraction logic
    climate_keywords = {
        "warm": ["warm", "hot", "sunny", "tropical"],
        "cold": ["cold", "cool", "snow", "winter"],
        "mild": ["mild", "moderate", "spring", "fall", "autumn"]
    }
    
    activity_keywords = {
        "outdoor": ["hiking", "biking", "swimming", "surfing", "skiing"],
        "cultural": ["museum", "history", "art", "architecture", "gallery"],
        "relaxation": ["relax", "spa", "beach", "resort", "peaceful"]
    }
    
    # Extract climate preferences
    for climate, words in climate_keywords.items():
        if any(word in text.lower() for word in words):
            if climate not in self.preferences.preferences:
                self.preferences.preferences.append(climate)
    
    # Extract activity preferences
    for activity, words in activity_keywords.items():
        if any(word in text.lower() for word in words):
            if activity not in self.preferences.preferences:
                self.preferences.preferences.append(activity)

# Example usage
def main():
    # Get API key from environment variable, or use the one from the original code if not set
    api_key = os.getenv("GROQ_API_KEY", "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")
        
    assistant = DestinationAssistant(api_key=api_key)
    
    assistant.speak("Hello! I can help you discover your ideal destination. Where would you like to go or what kind of place are you looking for?")
    
    while True:
        user_input = assistant.listen().strip()
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            assistant.speak("Goodbye! Have a great day.")
            break
            
        result = assistant.process_input(user_input)
        
        if result["status"] == "ready":
            assistant.speak("Destination confirmed! Handing off to booking system.")
            print(result["json_object"])
            break
        elif result["status"] == "error":
            assistant.speak(f"Sorry, there was an error: {result['error']}")
        else:
            assistant.speak(result["response"])
            
if __name__ == "__main__":
    main()