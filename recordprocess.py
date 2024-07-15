import os
import subprocess
from moviepy.editor import VideoFileClip, AudioFileClip
import cv2
print(cv2.__version__)
import numpy as np
import pyautogui
import time
import threading
import apivideo
#from selenium.webdriver.chrome.options import Options
#from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from PIL import Image, ImageDraw, ImageFont
from apivideo.api import videos_api
from apivideo import AuthenticatedApiClient
from apivideo.model.video_creation_payload import VideoCreationPayload
from apivideo.exceptions import ApiException
import logging
from fastapi import HTTPException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
#from selenium.webdriver.chrome.service import Service as ChromeService

# Set the DISPLAY environment variable for Xvfb
#os.environ['DISPLAY'] = ':99'
# Folder for saving videos
#folder_path = "C:/Users/nourt/output"
# Folder for saving videos (use environment variable or default to a relative path)
#logging.basicConfig(level=logging.DEBUG)
folder_path = os.getenv("OUTPUT_FOLDER", "output")
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# Paths to your output video
output_video_path = os.path.join(folder_path, "output.mp4")
branded_video_path = os.path.join(folder_path, "output_branded.mp4")
final_video_path = os.path.join(folder_path, "output_final.mp4")
sound_path = "./needs/sound.mp3"
logo_path = "./needs/ad.png"
#ffmpeg_path = "ffmpeg"  # Use the system-installed ffmpeg
#ffprobe_path = "ffprobe"
ffmpeg_path = "/usr/bin/ffmpeg"
ffprobe_path = "/usr/bin/ffprobe"
font_path="./needs/Poppins-SemiBold.ttf"


def log(message):
    print(f"[LOG] {message}")


def crop_pad_and_stretch_video(input_video_path, output_video_path, crop_height, logo_path, patient_name, doctor_name, nbr_months_duration, target_duration=30):
    # Get the original video duration
    ffprobe_command = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "format=duration",
        "-print_format", "default=noprint_wrappers=1:nokey=1",
        input_video_path
    ]
    result = subprocess.run(ffprobe_command, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"Error getting video duration: {result.stderr}")
        return

    original_duration = float(result.stdout.strip())
    
    # Calculate the setpts value
    setpts_value = target_duration / original_duration

    # Create the text overlay image
    overlay_image_path = create_text_overlay_image(patient_name,doctor_name,nbr_months_duration,)

    # Use ffmpeg to crop, pad, stretch, and overlay the text and logo
    ffmpeg_command = [
        ffmpeg_path,
        "-ss", "00:00:00.3",  # Start 0.3 seconds into the video
        "-i", input_video_path,
        "-i", logo_path,
        "-i", overlay_image_path,
        "-filter_complex", (
            f"[0:v]crop=iw:ih-{crop_height}:0:{crop_height},pad=iw:ih+{crop_height}:0:0:black,"
            f"setpts={setpts_value}*PTS[video];"
            f"[video][1:v]overlay=0:0[video_with_logo];"
            f"[video_with_logo][2:v]overlay=W-w-10:H-h-10"
        ),
        "-t", str(target_duration),
        "-y",  # Overwrite output file if it exists
        output_video_path
    ]
    subprocess.run(ffmpeg_command)



def create_text_overlay_image(patient_name,doctor_name,nbr_months_duration):
    # Create an image with the same size as the video frame
    width, height = 1280, 720
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Load the font
    font = ImageFont.truetype(font_path, 20)

    # Initialize ImageDraw
    draw = ImageDraw.Draw(image)

    # Draw the text
    draw.text((100, 37), patient_name, font=font, fill="white")
    draw.text((520, 37), f"{nbr_months_duration} mois", font=font, fill="white")
    draw.text((90, height - 45), f"Docteur: {doctor_name}", font=font, fill="white")

    # Save the image
    overlay_image_path = os.path.join(folder_path, "overlay_image.png")
    image.save(overlay_image_path)

    return overlay_image_path



def combine_audio_video(video_path, audio_path, output_path):
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path).subclip(0, 30)

    final_clip = video_clip.set_audio(audio_clip)
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

def process_video(patient_name,doctor_name,nbr_months_duration):
    if os.path.exists(output_video_path):
        crop_height = 70
        log("Cropping the top part of the video, adding padding to the bottom, stretching to 30 seconds, adding logo and text to the video...")
        crop_pad_and_stretch_video(output_video_path, branded_video_path, crop_height, logo_path,patient_name,doctor_name,nbr_months_duration)
        
        log(f"Branded video saved at: {branded_video_path}")
        log("Combining branded video with sound...")
        combine_audio_video(branded_video_path, sound_path, final_video_path)
        
        log(f"Final video saved at: {final_video_path}")
        os.remove(branded_video_path)
    else:
        log("Recording video not found for processing.")

def start_recording(stop_event, output, capture_interval):
    while not stop_event.is_set():
        try:
            screenshot = pyautogui.screenshot()
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized_frame = cv2.resize(frame, (1280, 720))
            output.write(resized_frame)
            #log("Frame captured and written to output.")
        except Exception as e:
            log(f"Error during recording: {e}")
        time.sleep(capture_interval)

def wait_for_element_to_be_clickable(driver, by, value, timeout=60):
    try:
        element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
        return element
    except TimeoutException:
        log(f"Element with {by}={value} not clickable within {timeout} seconds.")
        return None

def record_video(url):
    log("Script started.")
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--remote-debugging-pipe')
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--window-size=1920,1080")
    #chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")  # Required for running as root
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--remote-debugging-port=9222")  # Optional debugging port
    chrome_options.add_argument('--disable-dev-shm-usage')
    # Specify the path to the ChromeDriver
    #service = Service('/usr/local/bin/chromedriver')

    try:
        #driver = webdriver.Chrome(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(chrome_options)
        print(driver.title)
        #driver = webdriver.Chrome(options=chrome_options)
        log("Chrome driver initialized.")
        driver.get(url)
        log("URL opened.")
        time.sleep(5)

        driver.maximize_window()
        driver.execute_script("document.body.requestFullscreen();")
        log("Entered full-screen mode.")

        log("Waiting for the iframe to be available...")
        WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "OnyxCephWebGL")))
        log("Switched to iframe.")

        log("Waiting for the loading message to disappear...")
        WebDriverWait(driver, 100).until(EC.invisibility_of_element_located((By.ID, "loadingMsg")))
        log("Loading message disappeared.")

        resolution = (1280, 720)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        output_frame_rate = 24.0
        capture_interval = 1 / 85
        output = cv2.VideoWriter(output_video_path, fourcc, output_frame_rate, resolution)

        stop_event = threading.Event()
        recording_thread = threading.Thread(target=start_recording, args=(stop_event, output, capture_interval))
        recording_thread.start()

        try:
            time.sleep(2)
            log("Waiting for aniPlayBtn to be clickable...")
            ani_play_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "aniPlayBtn")))
            ani_play_button.click()
            log("aniPlayBtn clicked.")
            time.sleep(15)

            log("Waiting for viewUpperBtn to be clickable...")
            view_upper_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "viewUpperBtn")))
            view_upper_button.click()
            log("viewUpperBtn clicked.")
            time.sleep(2)
            
            log("Waiting for aniPlayBtn to be clickable again...")
            ani_play_button = wait_for_element_to_be_clickable(driver, By.ID, "aniPlayBtn", timeout=60)
            if ani_play_button:
                ani_play_button.click()
                log("aniPlayBtn clicked again.")
                time.sleep(15)
            
            log("Waiting for viewLowerBtn to be clickable...")
            view_lower_button = WebDriverWait(driver,60).until(EC.element_to_be_clickable((By.ID, "viewLowerBtn")))
            view_lower_button.click()
            log("viewLowerBtn clicked.")
            time.sleep(2)

            log("Waiting for aniPlayBtn to be clickable once more...")
            ani_play_button = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.ID, "aniPlayBtn")))
            ani_play_button.click()
            log("aniPlayBtn clicked once more.")
            time.sleep(15)

            # Click on viewFrontBtn
            log("Waiting for viewFrontBtn to be clickable...")
            view_front_button = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.ID, "viewFrontBtn")))
            view_front_button.click()
            log("viewFrontBtn clicked.")

             # Introduce a delay to observe the actions
            time.sleep(2)
            # Click on viewRotateBtn
            log("Waiting for viewRotateBtn to be clickable...")
            view_rotate_button = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.ID, "viewRotateBtn")))
            view_rotate_button.click()
            log("viewRotateBtn clicked.")
            # Introduce a delay to observe the actions
            time.sleep(1)

            # Click on aniPlayBtn again
            log("Waiting for aniPlayBtn to be clickable again...")
            ani_play_button = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.ID, "aniPlayBtn")))
            ani_play_button.click()
            log("aniPlayBtn clicked again.")
            
            # Introduce a delay to observe the actions
            time.sleep(15)
            
            # Double-click on viewRotateBtn
            log("Waiting for viewRotateBtn to be clickable for double-click...")
            view_rotate_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "viewRotateBtn")))
            view_rotate_button.click()
            view_rotate_button.click()  # Double-click
            log("viewRotateBtn double-clicked.")
            
            # Introduce a delay to observe the actions
            time.sleep(2)
            
            # Click on aniPlayBtn again
            log("Waiting for aniPlayBtn to be clickable once more...")
            ani_play_button = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.ID, "aniPlayBtn")))
            ani_play_button.click()
            log("aniPlayBtn clicked once more.")

            time.sleep(15)

        except TimeoutException:
            log("Loading took too much time!")

    finally:
        stop_event.set()
        recording_thread.join()
        output.release()
        cv2.destroyAllWindows()
        driver.quit()
        log("Chrome driver closed.")
        time.sleep(5)

        if os.path.exists(output_video_path):
            log(f"Video recording saved at: {output_video_path}")
        else:
            log("Failed to record the video.")

def clean_up():
    try:
        log("Cleaning up local files...")
        if os.path.exists(output_video_path):
            os.remove(output_video_path)
        if os.path.exists(branded_video_path):
            os.remove(branded_video_path)
        if os.path.exists(final_video_path):
            os.remove(final_video_path)
        overlay_image_path = os.path.join(folder_path, "overlay_image.png")
        if os.path.exists(overlay_image_path):
            os.remove(overlay_image_path)
        log("Local files cleaned up successfully.")
    except Exception as e:
        logging.error(f"Failed to clean up local files: {e}")

def upload_final_video(API_KEY):
    try:
        if not os.path.exists(final_video_path):
            logging.error(f"File not found: {final_video_path}")
            raise HTTPException(status_code=404, detail="Final video file not found")

        # Initialize the authenticated API client
        client = AuthenticatedApiClient(API_KEY)
        client.connect()
        videos_api_instance = videos_api.VideosApi(client)

        # Create a video object on api.video
        logging.info("Creating video object on api.video")
        video_creation_payload = VideoCreationPayload(
            title="Processed Video",
            description="A processed video.",
            public=True,
            mp4_support=True
        )
        video_object = videos_api_instance.create(video_creation_payload)
        video_id = video_object.video_id  # Accessing the attribute correctly
        logging.info(f"Video object created with ID: {video_id}")

        # Upload the video file to api.video
        logging.info(f"Uploading video file {final_video_path} to api.video")
        with open(final_video_path, "rb") as f:
            videos_api_instance.upload(video_id, f)

        # Get the player URL after upload
        video_info = videos_api_instance.get(video_id)
        player_url = video_info['assets']['player']
        logging.info(f"Video uploaded successfully. Player URL: {player_url}")

        return {"video_id": video_id, "player_url": player_url}
    except ApiException as e:
        logging.error(f"API exception occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Video upload failed: {e}")
    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Video upload failed: {e}")


if __name__ == "__main__":
    test_video_processing_with_sample_data()
