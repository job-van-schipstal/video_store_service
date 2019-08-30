"""
Responsible for recording from the IP camera

Uses the apiclient to get video stream and pipes it to ffmpeg,
which handles the actual capture and optionally the recoding.
"""
import subprocess, os, requests, logging
from threading import Thread
from time import sleep
from typing import List, Tuple, Dict, Any

from video_store_service import apiclient

# Recording may take at most 15 times the supposed recording duration

timeout_multiplier = 15

#Video folder
video_folder = 'videos'

#test_filename
test_filename = 'test.mp4'


def data_streamer_thread(ffmpeg: subprocess.Popen, request: requests.Response):
    """
    While ffmpeg is running, reads data from Response class (the camera) and writes it to ffmpeg
    :param ffmpeg: ffmpeg process
    :param request: request class with video stream
    :return: nothing
    """
    for data in request.iter_content(chunk_size=None, decode_unicode=False):
        #    #if ffmpeg is done, we are too
        if (ffmpeg.poll() is not None):
            print('ffmpeg returned {ffmpeg.returncode()}')
            break
        try:
            ffmpeg.stdin.write(data)
        # Either ffmpeg crashed, or it wants no more data, stop sending either way
        except BrokenPipeError:
            break


def get_ffmpeg_command(file_name: str,
                       video_config: Dict[str, Any]) -> List[str]:
    """
    Generates list
    used by Popen to start ffmpeg
    :param file_name: name of the output file (with file extension)
    :param video_config: Dict with video configuration options
    :return: List with ffmpeg and its command line parameters
    """
    # Main cmd
    cmd = ['ffmpeg']

    # Add input framerate if defined
    if video_config.get('framerate', 'auto') != 'auto':
        cmd.append('-r'); cmd.append(str(video_config.get('framerate', 30)))

    # Add pipe input and recording duration
    cmd.append('-i'); cmd.append('pipe:0')
    cmd.append('-t'); cmd.append(str(video_config.get('duration', 10)))

    # If not debug, decrease ffmpeg verbosity to warning and up
    if not video_config.get('debug_info', False):
        cmd.append('-hide_banner')
        cmd.append('-loglevel'); cmd.append('warning')

    # If recoding, add libx264 video codec with fast encoding present
    if video_config.get('recode', True):
        cmd.append('-c:v'); cmd.append('libx264')
        cmd.append('-preset'); cmd.append('ultrafast')

    # Add output filename
    cmd.append('-an'); cmd.append(str(file_name))
    logging.debug(cmd)
    return cmd


def run_ffmpeg_and_record(cmd: List[str],
                          duration: int,
                          access: requests.Response) -> Tuple[bool, str]:
    """
    Function that starts the recording
    Creates an instance of ffmpeg with the cmd it has been given
    Spawns a thread that will pipe the video stream to ffmpeg
    monitors that ffmpeg closes before duration * timeout_multiplier
    Kills it if it doesn't

    :param cmd: list of ffmpeg and its command line parameters
    :param duration: int duration of recording, to determine timeout
    :param access: reponse object with active connection to IP camera
                   Will be used to pipe the video stream to ffmpeg

    :return: Tuple[boolean success, string message]
    """
    logging.debug('Start FFmpeg')
    ffmpeg = subprocess.Popen(cmd,
                              stdin=subprocess.PIPE,
                              stdout=None,
                              stderr=None,
                              cwd=os.path.join(os.getcwd(), video_folder))

    logging.debug('Start streaming recieved data to ffmpeg')
    stream_thread = Thread(name='data_stream_thread',
                           target=data_streamer_thread,
                           args=(ffmpeg, access))
    stream_thread.start()

    ### Wrapup safety code ###
    # Recording may take at most duration * timeout_multiplier seconds
    for i in range(1, duration * timeout_multiplier):
        # If ffmpeg is done, return
        if ffmpeg.poll() is not None:
            return True, f'FFMPEG finished successfully in about {i} seconds'
        # else wait
        sleep(1)

    # Force terminate if not done
    if ffmpeg.poll() is not None:
        logging.warning('Force FFMPEG termination')
        ffmpeg.terminate()
        sleep(1)
        if ffmpeg.poll() is not None:
            ffmpeg.kill()
        return False, f'FFMPEG required forcefull termination'
    logging.debug('Done!')
    return True, f'FFMPEG stopped at the last minute'


class FFMPEGRecorder():
    """
    Class for recording videostream with ffmpeg
    """
    def __init__(self, config: Dict[str, Any], client: apiclient.Client):
        """
        :param config: Dict with configuration options
        :param client: Apiclient class instance to get the video stream from
        """
        self.__config = config
        self.__client = client

    def record(self, file_name: str) -> Tuple[bool, str]:
        """
        :param file_name: file_name of output file (with file extension)
        :return: Tuple[success: bool, message: str]
        """
        # Get webaccess to camera
        access = self.__client.get_webaccess_connection(self.__config['camera'])

        # Record using ffmpeg
        cmd = get_ffmpeg_command(file_name, self.__config['video'])
        return run_ffmpeg_and_record(cmd, self.__config['video'].get('duration'), access)

    def do_test_run(self) -> bool:
        """
        Records from IP camera without being triggered by a webhook
        Ensures there is a subfolder Video's
        Removes the previous test file if it is still there
        Usefull to test if you configured the recording properly
        :return: success: bool
        """
        # Make folder if it isn't there yet
        folder = os.path.join(os.getcwd(), 'videos')
        os.makedirs(folder, exist_ok=True)

        # Remove previous test video file
        video_file = os.path.join(folder, test_filename)
        if os.path.isfile(video_file):
            os.unlink(video_file)

        # Test recording
        logging.info('Testing recording')
        result = self.record(test_filename)
        if result[0]:
            logging.info('recording was successful, saved file in folder '
                         '%s, with name %s', video_folder, test_filename)
            return True
        logging.info('recording failed with message: %s', result[1])
        return False
