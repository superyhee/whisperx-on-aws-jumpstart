from dotenv import load_dotenv

load_dotenv()


import streamlit as st
import yt_dlp
import subprocess
import os
import re
import whisperx_transcribe
import tempfile

def extract_video_id(url):
    regex = r"(?<=v=)[^&#]+|(?<=be/)[^&#]+"
    match = re.search(regex, url)
    return match.group(0) if match else None

def extract_audio(video_path, audio_path):
    command = ['ffmpeg', '-i', video_path, '-vn', '-y', audio_path]
    subprocess.run(command, check=True)

def download(video_id: str) -> str:
    video_id = video_id.strip()
    video_url = f'https://www.youtube.com/watch?v={video_id}'
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'paths': {'home': 'audio/'},
        'outtmpl': {'default': '%(id)s.%(ext)s'},
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        error_code = ydl.download([video_url])
        if error_code != 0:
            raise Exception('Failed to download video')

    return f'audio/{video_id}.m4a'

def process(youtube_url, language):
    video_id = extract_video_id(youtube_url)
    if not video_id:
        st.error("Invalid YouTube URL")
        return

    try:
        progress_text = "Downloading video..."
        progress_value = 0
        progress_bar = st.progress(progress_value, text=progress_text)
        audio_file = download(video_id)
        progress_value = 33
        progress_bar.progress(progress_value, text=progress_text)
    except Exception as e:
        st.error(f"Failed to download video: {e}")
        return

    audio_file_mp3 = 'audio/audio.mp3'
    progress_text = "Converting audio format..."
    progress_value = 66
    progress_bar.progress(progress_value, text=progress_text)
    subprocess.run(['ffmpeg', '-i', audio_file, '-y', audio_file_mp3], check=True)

    progress_text = "Transcribing audio..."
    progress_value = 70
    progress_bar.progress(progress_value, text=progress_text)
    transcription = whisperx_transcribe.transcribe(audio_file_mp3, "medium", language=language)
    progress_text = "Transcribing completed..."
    progress_value = 100
    progress_bar.progress(progress_value, text=progress_text)
    st.write(transcription)
    # Remove temporary files
    os.remove(audio_file)
    os.remove(audio_file_mp3)


def main():
    st.title("Audio Transcription")

    tabs = st.tabs(["YouTube Video", "MP3 File"])

    with tabs[0]:
        youtube_url = st.text_input("Enter YouTube URL")
        language = st.text_input("Enter language code (e.g., en, fr, es)", key="youtube_language")

        transcribe_button = st.button("Transcribe",key="url")

        if transcribe_button:
           
            #transcribe_button = st.button("Transcribe", disabled=True)  # Disable the button
            process(youtube_url, language)
            #transcribe_button = st.button("Transcribe")  # Enable the button after processing
            

    with tabs[1]:
        mp3_file = st.file_uploader("Upload MP3 File", type=["mp3"])
        language = st.text_input("Enter language code (e.g., en, fr, es)", key="mp3_language")
        transcribe_mp3_button = st.button("Transcribe",key="mp3")

        if transcribe_mp3_button:
            progress_text = "Processing MP3 file..."
            progress_value = 10
            progress_bar = st.progress(progress_value, text=progress_text)
            # Save the uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(mp3_file.getvalue())
                tmp_file_path = tmp_file.name

            transcription = whisperx_transcribe.transcribe(tmp_file_path, "medium", language=language)
            st.write(transcription)
            progress_value = 100
            progress_text = "Processing completed..."
            progress_bar.progress(progress_value, text=progress_text)

            # Remove the temporary file
            os.unlink(tmp_file_path)

if __name__ == "__main__":
    main()
