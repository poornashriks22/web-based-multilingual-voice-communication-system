# utils.py
import os
import tempfile
from gtts import gTTS
import requests
import json

def text_to_speech(text, language='en'):
    """
    Convert text to speech in specified language
    Returns: (audio_data, error_message)
    """
    try:
        # Clean and prepare text
        text = text.strip()
        if not text:
            return None, "No text provided"
        
        # Map language codes to gTTS codes
        lang_map = {
            'en': 'en',
            'ta': 'ta',
            'hi': 'hi',
            'ml': 'ml',
            'te': 'te',
            'kn': 'kn'
        }
        
        tts_lang = lang_map.get(language, 'en')
        
        # Create gTTS object with specific parameters for Indian languages
        tts = gTTS(
            text=text,
            lang=tts_lang,
            slow=False,  # Normal speed
            lang_check=True  # Check if language is supported
        )
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_path = temp_file.name
        
        try:
            tts.save(temp_path)
            
            # Read the audio file
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            return audio_data, None
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        # Fallback to English if language not supported
        if "not a language" in str(e).lower() or "not supported" in str(e).lower():
            try:
                # Try with English as fallback
                tts = gTTS(text=text, lang='en')
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_path = temp_file.name
                tts.save(temp_path)
                
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                # Clean up
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
                return audio_data, f"Language {language} not fully supported. Using English."
            except:
                return None, f"Error: {str(e)}"
        return None, f"Error: {str(e)}"


def convert_english_to_language(text, target_language='en'):
    """
    Convert English text to speech in target language
    This is the main function for your use case
    """
    return text_to_speech(text, target_language)


# Alternative: Using Google Translate API (if gTTS doesn't work)
def translate_and_speak(text, target_lang='en'):
    """
    Alternative method using translation + speech
    Requires: pip install googletrans==4.0.0-rc1
    """
    try:
        from googletrans import Translator
        import tempfile
        
        # Translate text first
        translator = Translator()
        translated = translator.translate(text, dest=target_lang)
        
        # Convert translated text to speech
        return text_to_speech(translated.text, target_lang)
        
    except Exception as e:
        # Fallback to direct text-to-speech
        return text_to_speech(text, target_lang)