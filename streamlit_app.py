import streamlit as st
from misc07 import DestinationAssistant
import os
import speech_recognition as sr
import threading
import json

# Initialize the assistant
@st.cache_resource
def get_assistant():
    api_key = os.getenv("GROQ_API_KEY", "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")
    return DestinationAssistant(api_key)

assistant = get_assistant()

# Flag to control speech output
if "is_speaking" not in st.session_state:
    st.session_state.is_speaking = False

# Initialize preferences if not already in session state
if "preferences" not in st.session_state:
    st.session_state.preferences = assistant.preferences

# Streamlit app
def main():
    st.title("Travel Destination Assistant")
    
    # Initialize session state for conversation history
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
        # Add initial greeting
        st.session_state.conversation.append({
            "role": "assistant", 
            "content": "Hello! I can help you discover your ideal destination. Where would you like to go or what kind of place are you looking for?"
        })
        # Sync conversation history with assistant
        assistant.conversation_history = [
            {"role": "assistant", "content": st.session_state.conversation[0]["content"]}
        ]
    
    # Display conversation history
    for message in st.session_state.conversation:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Show current preferences in sidebar
    st.sidebar.title("Current Preferences")
    preferences = st.session_state.preferences
    st.sidebar.write(f"Destination: {preferences.destination or 'Not specified'}")
    st.sidebar.write(f"Preferences: {', '.join(preferences.preferences) if preferences.preferences else 'None'}")
    st.sidebar.write(f"Suggested Destinations: {', '.join(preferences.suggested_destinations) if preferences.suggested_destinations else 'None'}")
    
    # Voice input button with proper error handling
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎤 Speak"):
            with st.spinner("Listening..."):
                try:
                    user_input = assistant.listen()
                    
                    if user_input.startswith("Sorry") or "not found" in user_input:
                        st.warning(user_input)
                    else:
                        # Process valid voice input
                        process_user_input(user_input)
                except Exception as e:
                    st.error(f"Error with voice input: {str(e)}")
    
    # Stop speaking button
    with col2:
        if st.button("🛑 Stop Speaking") and st.session_state.is_speaking:
            stop_speaking()
            st.session_state.is_speaking = False
            st.success("Voice output stopped")
            st.rerun()
    
    # Text input
    user_input = st.chat_input("Type your message...")
    if user_input:
        process_user_input(user_input)

def stop_speaking():
    """Stop the text-to-speech engine"""
    if hasattr(assistant.engine, 'endLoop'):
        assistant.engine.endLoop()

def speak_with_control(text):
    """Speak text with ability to stop"""
    st.session_state.is_speaking = True
    
    # Define a function to run in a thread
    def run_speech():
        try:
            assistant.engine.say(text)
            assistant.engine.runAndWait()
        except:
            pass
        finally:
            st.session_state.is_speaking = False
    
    # Run in a separate thread
    threading.Thread(target=run_speech, daemon=True).start()

def process_user_input(user_input):
    """Process user input and update the conversation"""
    # Add user input to conversation history
    st.session_state.conversation.append({"role": "user", "content": user_input})
    
    # Process user input
    result = assistant.process_input(user_input)
    
    # Add assistant response to conversation history
    assistant_response = result.get("response", "Sorry, I couldn't process your request.")
    st.session_state.conversation.append({"role": "assistant", "content": assistant_response})
    
    # Update the session state with the latest preferences
    st.session_state.preferences = assistant.preferences
    
    # If destination is confirmed, display JSON data
    if result.get("status") == "ready":
        st.json(result.get("json_object"))
    
    # Speak the response if not already speaking
    if not st.session_state.is_speaking:
        speak_with_control(assistant_response)
    
    # Force a rerun to update the UI with new messages
    st.rerun()

# Run the app
if __name__ == "__main__":
    main()