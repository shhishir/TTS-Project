from flask import Flask, render_template, request, send_from_directory, url_for
import pyttsx3
import os
import uuid  # For unique filenames
import platform  # To provide OS-specific advice
import threading  # For thread safety

app = Flask(__name__)
UPLOAD_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the output directory exists
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
tts_lock = threading.Lock()  # Lock for thread safety


def text_to_speech_pyttsx3(text, output_filename):
    """
    Converts text to speech using pyttsx3 and saves it to a file.
    """
    engine = pyttsx3.init()

    # --- Optional: Voice Customization ---
    # You can list available voices and set a preferred one.
    # voices = engine.getProperty('voices')
    # For example, to set a specific voice (index might vary):
    # if voices:
    #     if platform.system() == "Windows":
    #         # Example: engine.setProperty('voice', voices[0].id) # Often David or Zira
    #         pass # Default is usually fine
    #     elif platform.system() == "Darwin": # macOS
    #         # engine.setProperty('voice', 'com.apple.speech.synthesis.voice.daniel') # Example
    #         pass
    #     else: # Linux
    #         # engine.setProperty('voice', 'english-us') # Example, depends on espeak voices
    #         pass

    # engine.setProperty('rate', 150)  # Speed of speech (words per minute)
    # engine.setProperty('volume', 0.9) # Volume (0.0 to 1.0)
    # --- End Optional Customization ---

    with tts_lock:  # Ensure thread safety
        try:
            engine.save_to_file(text, output_filename)
            engine.runAndWait()
            return True
        except Exception as e:
            print(f"pyttsx3 error: {e}")
            return False


@app.route("/", methods=["GET"])
def index():
    # Clean up old files if needed (optional, for a long-running app)
    # for f in os.listdir(app.config['UPLOAD_FOLDER']):
    #     os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
    return render_template("index.html", audio_file=None)


@app.route("/synthesize", methods=["POST"])
def synthesize():
    text_input = request.form.get("text_input")

    if not text_input or not text_input.strip():
        return render_template(
            "index.html",
            error="Text cannot be empty. Please enter some text.",
            audio_file=None,
        )

    # Generate a unique filename to prevent overwriting and browser caching issues
    filename = f"speech_{uuid.uuid4()}.mp3"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    success = text_to_speech_pyttsx3(text_input, filepath)

    if success and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return render_template(
            "index.html", audio_file=filename, submitted_text=text_input
        )
    else:
        error_message = (
            "Failed to generate audio. The file might be empty or an error occurred."
        )
        print(f"pyttsx3 boolean responce is: {success}")
        if not success:
            error_message = "An error occurred with the TTS engine."
        if os.path.exists(filepath):  # remove empty/corrupt file
            os.remove(filepath)
        return render_template(
            "index.html",
            error=error_message,
            audio_file=None,
            submitted_text=text_input,
        )


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"], filename, as_attachment=True
    )


if __name__ == "__main__":
    print("Starting Flask Text-to-Speech App...")
    print("Important: `pyttsx3` relies on system-installed speech engines.")
    print("- On macOS: Uses NSSpeechSynthesizer (should work out-of-the-box).")
    app.run(debug=True, port=5000)
