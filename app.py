from flask import Flask, render_template, request, send_from_directory, url_for
import pyttsx3
import os
import uuid  # For unique filenames
import platform  # To provide OS-specific advice

app = Flask(__name__)
UPLOAD_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the output directory exists
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

MACOS_PREFERRED_VOICES = [
    "com.apple.voice.compact.en-US.Samantha",
    "com.apple.speech.synthesis.voice.Albert",
    "com.apple.speech.synthesis.voice.Alex",
    "com.apple.voice.compact.en-GB.Daniel",  # Original default
]


def tts_ppyttsx(text, output_audio_file):
    """
    Converts text to speech using pyttsx3 and saves it to the specified filepath.
    On macOS, attempts to set a preferred voice robustly.
    Expects full_output_filepath to have the desired extension (e.g., .m4a).
    Returns True on success, False on failure.
    """
    print(f"Attempting to synthesize text: '{text}' to file: '{output_audio_file}'")
    try:
        engine = pyttsx3.init()
        if engine is None:
            print("!!! pyttsx3.init() failed. returned None.")
            return False

        current_os = platform.system()

        if current_os == "Darwin":
            voices_avialable = engine.getProperty("voices")
            avilable_voice_ids = [v.id for v in voices_avialable]

            selected_voice_id = None

            for preferred_id in MACOS_PREFERRED_VOICES:
                if preferred_id in avilable_voice_ids:
                    selected_voice_id = preferred_id
                    break

            if not selected_voice_id:
                selected_voice_id = engine.getProperty("voice")
                print(
                    f"!!! WARNING: Preferred voice not found. Using default voice instead: {selected_voice_id}."
                )
            if selected_voice_id:
                engine.setProperty("voice", selected_voice_id)

                current_voice_check = engine.getProperty("voice")
                if current_voice_check == selected_voice_id:
                    print(f"SUCCESS: Voice robustly set to {selected_voice_id}")
                else:
                    # This can happen if the voice ID was invalid or engine couldn't switch
                    print(
                        f"!!! WARNING: Failed to robustly set voice to {selected_voice_id}. Current is: {current_voice_check}. Proceeding with current."
                    )
            else:
                print(
                    "!!! WARNING: Could not determine a voice to set on macOS. Using absolute default."
                )
        else:
            # For other OS (Windows, Linux), just use default or existing logic
            print(
                f"DEBUG: Running on {current_os}. Using default pyttsx3 voice behavior."
            )

        # Set properties for the speech engine
        engine.setProperty("rate", 180)
        engine.setProperty("volume", 0.9)

        # Set the output audio file format based on the file extension
        engine.save_to_file(text, output_audio_file)

        # Run the engine to process the text and save it to the file
        engine.runAndWait()

        # Clean up the engine instance
        del engine

        if os.path.exists(output_audio_file) and os.path.getsize(output_audio_file) > 0:
            print(
                f"SUCCESS: File '{output_audio_file}' created. Size: {os.path.getsize(output_audio_file)} bytes."
            )
            return True
        elif os.path.exists(output_audio_file):
            print(f"!!! FAILURE: File '{output_audio_file}' was created BUT IS EMPTY.")
            os.remove(output_audio_file)  # Clean up empty file
            return False
        else:
            print(f"!!! FAILURE: File '{output_audio_file}' was NOT created.")
            return False
    except Exception as e:
        print(f"!!! EXCEPTION during standalone test: {e}")
        import traceback

        traceback.print_exc()
        return False


@app.route("/", methods=["GET"])
def index():
    # Clean up old files if needed (optional, for a long-running app)
    # for f in os.listdir(app.config["UPLOAD_FOLDER"]):
    # os.remove(os.path.join(app.config["UPLOAD_FOLDER"], f))
    return render_template("index.html", audio_url=None)


@app.route("/synthesize", methods=["POST"])
def synthesize():
    text_input = request.form.get("text_input")

    if not text_input or not text_input.strip():
        return render_template(
            "index.html",
            error="Text cannot be empty. Please enter some text.",
            audio_url=None,
        )

    # Generate a unique filename to prevent overwriting and browser caching issues
    filename = f"speech_{uuid.uuid4()}.m4a"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    success = tts_ppyttsx(text_input, filepath)

    if success and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        # Pass the URL for playing the audio to the template
        audio_play_url = url_for("serve_audio_file", filename=filename)
        return render_template(
            "index.html",
            audio_url=audio_play_url,
            audio_filename=filename,
            submitted_text=text_input,
        )
    else:
        error_message = (
            "Failed to generate audio. The file might be empty or an error occurred."
        )
        if not success:
            error_message = "An error occurred with the TTS engine."
        if os.path.exists(filepath):  # remove empty/corrupt file
            if os.path.getsize(filepath) == 0:
                os.remove(filepath)
        return render_template(
            "index.html",
            error=error_message,
            audio_url=None,
            submitted_text=text_input,
        )


# Serve the audio file for the <audio> tag
@app.route("/audio/<filename>")
def serve_audio_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"], filename, as_attachment=False
    )


if __name__ == "__main__":
    print("Starting Flask Text-to-Speech App...")
    print("Using .m4a for audio output, especially for macOS compatibility.")
    app.run(debug=True, port=5000)
