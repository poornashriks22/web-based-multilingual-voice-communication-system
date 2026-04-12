# windows_test.py - Test script for Windows
import os
import sys

print("🔧 Windows TTS Test")
print("=" * 50)

# Check Python version
print(f"Python version: {sys.version}")

# Check temp directory
temp_dir = os.environ.get('TEMP', 'C:\\Temp')
print(f"Temp directory: {temp_dir}")

# Test if we can create and delete files in temp
test_file = os.path.join(temp_dir, 'test_delete.txt')
try:
    with open(test_file, 'w') as f:
        f.write('test')
    
    os.unlink(test_file)
    print("✅ File creation/deletion test: PASSED")
except Exception as e:
    print(f"❌ File creation/deletion test: FAILED - {e}")

# Now test TTS
print("\n🎯 Testing TTS...")
try:
    from translation_tts import text_to_speech_safe
    
    test_text = "Hello Windows, this is a test."
    
    for lang_code in ['en', 'ta', 'hi']:
        print(f"\nTesting {lang_code}:")
        audio, error = text_to_speech_safe(test_text, lang_code, use_in_memory=True)
        
        if audio:
            # Save to current directory (not temp)
            filename = f"tts_test_{lang_code}.mp3"
            with open(filename, 'wb') as f:
                f.write(audio)
            
            file_size = os.path.getsize(filename)
            print(f"  ✅ Success! File: {filename}")
            print(f"  📊 Size: {file_size:,} bytes")
            
            # Try to play it
            try:
                import winsound
                # Play a beep to indicate success
                winsound.Beep(1000, 200)
            except:
                pass
        else:
            print(f"  ❌ Failed: {error}")
            
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n💡 Install required packages:")
    print("pip install gtts googletrans")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n" + "=" * 50)
print("Test complete!")