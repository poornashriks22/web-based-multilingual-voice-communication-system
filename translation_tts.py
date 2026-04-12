# translation_tts.py - WINDOWS FIXED VERSION
from googletrans import Translator
from gtts import gTTS
import tempfile
import os
import time
import threading

# Initialize translator
translator = Translator()

def translate_text(text, target_lang='ta'):
    """Translate English text to target language"""
    try:
        translation = translator.translate(text, dest=target_lang)
        return translation.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Fallback to English

def safe_delete_file(filepath, max_attempts=5):
    """Safely delete a file with retries for Windows file locking issues"""
    for attempt in range(max_attempts):
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
                return True
        except (PermissionError, OSError) as e:
            if attempt < max_attempts - 1:
                time.sleep(0.1)  # Wait 100ms before retrying
            else:
                print(f"Failed to delete file after {max_attempts} attempts: {filepath}")
                print(f"Error: {e}")
                return False
    return False

def text_to_speech_multilingual(text, target_language='en'):
    """
    Convert English text to speech in target language
    Windows-safe version with proper file handling
    """
    
    # Language mapping for gTTS
    language_map = {
        'en': 'en',      # English
        'ta': 'ta',      # Tamil
        'hi': 'hi',      # Hindi
        'ml': 'ml',      # Malayalam
        'te': 'te',      # Telugu
        'kn': 'kn'       # Kannada
    }
    
    temp_path = None
    try:
        # Clean the text
        text = str(text).strip()
        if not text:
            return None, "No text provided"
        
        # If target language is English, use direct TTS
        if target_language == 'en':
            tts = gTTS(text=text, lang='en', slow=False)
        else:
            # For Indian languages, first translate the text
            translated_text = translate_text(text, target_language)
            print(f"Translated to {target_language}: {translated_text[:50]}...")
            
            # Then convert to speech using gTTS with the translated text
            tts_lang = language_map.get(target_language, 'en')
            tts = gTTS(text=translated_text, lang=tts_lang, slow=False)
        
        # Create a unique temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix='.mp3',
            prefix='tts_'
        )
        temp_path = temp_file.name
        temp_file.close()  # Close the file handle immediately
        
        # Save the TTS to file
        tts.save(temp_path)
        
        # Small delay to ensure file is fully written
        time.sleep(0.1)
        
        # Read the audio file content
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        
        # Verify audio data
        if not audio_data or len(audio_data) < 100:
            raise Exception("Generated audio file is empty or too small")
        
        return audio_data, None
        
    except Exception as e:
        print(f"TTS error for {target_language}: {e}")
        
        # Fallback to English
        try:
            fallback_tts = gTTS(text=text, lang='en', slow=False)
            
            # Create new temp file for fallback
            fallback_temp = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='_fallback.mp3',
                prefix='tts_'
            )
            fallback_path = fallback_temp.name
            fallback_temp.close()
            
            fallback_tts.save(fallback_path)
            time.sleep(0.1)
            
            with open(fallback_path, 'rb') as f:
                fallback_audio = f.read()
            
            # Clean up fallback temp file
            safe_delete_file(fallback_path)
            
            return fallback_audio, f"Using English (fallback): {str(e)}"
            
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            return None, f"Complete failure: {str(e2)}"
            
    finally:
        # Always clean up the main temp file
        if temp_path and os.path.exists(temp_path):
            safe_delete_file(temp_path)

# Alternative: Using in-memory buffer (no file operations)
def text_to_speech_in_memory(text, target_language='en'):
    """
    Convert text to speech without saving to file first
    More reliable for Windows
    """
    try:
        from io import BytesIO
        
        # Clean the text
        text = str(text).strip()
        if not text:
            return None, "No text provided"
        
        # Handle translation if needed
        if target_language == 'en':
            tts_text = text
            tts_lang = 'en'
        else:
            translated_text = translate_text(text, target_language)
            tts_text = translated_text
            tts_lang = target_language
        
        # Create TTS object
        tts = gTTS(text=tts_text, lang=tts_lang, slow=False)
        
        # Save to in-memory buffer
        buffer = BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        audio_data = buffer.getvalue()
        buffer.close()
        
        if not audio_data or len(audio_data) < 100:
            raise Exception("Generated audio is empty or too small")
        
        return audio_data, None
        
    except Exception as e:
        print(f"In-memory TTS error for {target_language}: {e}")
        
        # Fallback to English in-memory
        try:
            fallback_tts = gTTS(text=text, lang='en', slow=False)
            buffer = BytesIO()
            fallback_tts.write_to_fp(buffer)
            buffer.seek(0)
            fallback_audio = buffer.getvalue()
            buffer.close()
            
            return fallback_audio, f"Using English (fallback): {str(e)}"
            
        except Exception as e2:
            print(f"In-memory fallback also failed: {e2}")
            return None, f"Complete failure: {str(e2)}"

# Main function - uses in-memory by default (more reliable)
def text_to_speech_safe(text, target_language='en', use_in_memory=True):
    """
    Safe text-to-speech conversion with Windows compatibility
    """
    if use_in_memory:
        return text_to_speech_in_memory(text, target_language)
    else:
        return text_to_speech_multilingual(text, target_language)


# Test function
def test_all_languages_safe():
    """Test all languages with safe method"""
    test_text = "Hello, how are you? This is a test message."
    
    languages = [
        ('en', 'English'),
        ('ta', 'Tamil'),
        ('hi', 'Hindi'),
        ('ml', 'Malayalam'),
        ('te', 'Telugu'),
        ('kn', 'Kannada')
    ]
    
    print("🎯 Testing Safe Multilingual TTS (In-Memory Method)")
    print("=" * 60)
    
    for code, name in languages:
        print(f"\n🔊 Testing {name} ({code}):")
        print(f"   Original text: '{test_text}'")
        
        # Use in-memory method (more reliable)
        audio, error = text_to_speech_safe(test_text, code, use_in_memory=True)
        
        if audio:
            # Save test file
            import os
            os.makedirs('output_safe', exist_ok=True)
            
            filename = f"output_safe/test_{code}_{name}.mp3"
            with open(filename, 'wb') as f:
                f.write(audio)
            
            print(f"   ✅ Success! Saved as {filename}")
            print(f"   📊 File size: {len(audio):,} bytes")
            
            # Try to play it (optional)
            # try:
            #     import playsound
            #     playsound.playsound(filename)
            # except:
            #     pass
            
        if error:
            print(f"   ⚠ Warning: {error}")

if __name__ == "__main__":
    test_all_languages_safe()
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("📁 Check the 'output_safe' folder for generated audio files.")