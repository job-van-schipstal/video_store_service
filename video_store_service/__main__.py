""""
Main file & entrypoint for project
In charge of loading configuration, parsing command line arguments,
and then performing the required actions:
- run configuration utility
- do a test run
- start webhook listener
"""
import os, yaml, argparse, logging, sys, json
from flask import Flask, jsonify, request
from queue import Queue
from threading import Thread
from shutil import copyfile
from typing import Dict, Any, Optional

from video_store_service import apiclient, record, config_util

# Configuration files
template_config_file = 'config.yml.template'
config_file = 'config.yml'

def load_config() -> Dict[str, Any]:
    """
    Loads YAML configuration file
    if it does not exists, copy template onto it first
    :return Dict with all configuration
    """
    if not os.access(config_file, os.R_OK):
        copyfile(template_config_file, config_file)
    with open(config_file, "r") as yml_f:
        return yaml.safe_load(yml_f)


def record_thread(ffmpeg_recorder: record.FFMPEGRecorder, q: Queue):
    """
    Consumer from the webhook Queue
    Processes the webhooks one by one
    :param ffmpeg_recorder: recorder to use
    :param q: the queue with the webhook calls
    :return: nothing
    """
    while True:
        try:
            name = q.get()
            result = ffmpeg_recorder.record(name)
            if result[0]:
                print(f'Recording finished, saved as {name}')
            else:
                print(f'Recording failed with message {result[1]}')
        except KeyboardInterrupt:
            return
        except ValueError:
            logging.error('ValueError during recording', exc_info=True)


def get_name(hook: Dict[Any, Any]) -> Optional[str]:
    """
    Creates a name based on the webhook call it recieved
    Format: Timestamp_Devicename.mp4
    Removes any characters that are not regular characters, numbers, '_' '.' or '-'
    to ensure the filename is valid
    :param hook: Dict with webhook response
    :return: filename: str, None if invalid hook failed
    """
    if 'extraInfo' not in hook:
        return
    timestamp = hook.get('createdOn', '').replace(':', '-')
    device_name = hook['extraInfo'].get('Device name', '').replace(' ', '_')
    if timestamp == '' or device_name == '':
        return
    name = f'{timestamp}_{device_name}.mp4'
    # https://stackoverflow.com/questions/7406102/create-sane-safe-filename-from-any-unsafe-string
    file_name = "".join([c for c in name if
                         c.isalpha()
                         or c.isdigit()
                         or c == '_'
                         or c == '.'
                         or c == '-']).rstrip()
    return file_name


def create_app() -> Flask:
    """
    Entrypoint for flask app
    Creates Flask app and configures it
    Creates a queue for the webhooks and a thread that processes them
    """
    app = Flask(__name__)

    # Create queue for recording, so only one will be recorded at a time
    q: Queue = Queue(int(config['webhooks'].get('queue_size', 10)))

    # Start thread which will take care of the recording
    t = Thread(name='data_recorder_thread',
               target=record_thread,
               args=(recorder, q))
    t.start()

    # Definition of the api route
    # We basically have a webserver that only accepts Post requests on /webhook
    @app.route("/webhook", methods=['POST'])
    def webhook():
        data = request.json
        # if content not None
        if data:
            hook = json.loads(data)
            # If there is space, add to the queue
            if not q.full():
                name = get_name(hook)
                if name is not None:
                    q.put(name)
                    logging.info('Received webhook, will be saved as %s', name)
                    return jsonify({'success': True})
        return jsonify({'success': False})
    return app


# Get configuration Dict and an instance of the apiclient and recorder
# Not inside if statement because it is also needed for the wsgi entry
config = load_config()
client = apiclient.Client(config['IXON_api'])
recorder = record.FFMPEGRecorder(config, client)

if __name__ == '__main__':
    """
    Entrypoint for calling this module
    Command line interface to tell this application what to do
    """

    # Configure commandline arguments
    parser = argparse.ArgumentParser(description='IXON Video Store Service',
                                     usage='python -m video_store_service '
                                           '[-h] [-c] [-t] [-w] [-p PORT] [-d]')

    parser.add_argument('-c', '--configure',
                        action='store_true',
                        help='Opens configuration utility. '
                             'A short wizard to help you configure this module.')

    parser.add_argument('-t', '--test-recording',
                        action='store_true',
                        help='Immediately record, as if the webhook was called. '
                             'Useful for testing the recording settings.')

    parser.add_argument('-w', '--webhook',
                        action='store_true',
                        help='Enable webhook listener')

    parser.add_argument('-p', '--port',
                        action='store',
                        default=8080,
                        help='Webhook listener port (default: 8080)')

    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help='Enable debugging information')

    # Parse according to this configuration
    args = parser.parse_args()

    # Set logginglevel based on debug
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    # If nothing was enabled, display help & exit
    if args.configure is False and args.test_recording is False and args.webhook is False:
        parser.print_help()
        sys.exit()

    # Configurator utility script
    if args.configure:
        config_util.run_configuration_utility(config, client)

    # Test Recording
    if args.test_recording:
        recorder.do_test_run()

    # Setup Flask webserver so we can listen to webhooks
    # Flask's build in webserver (werkzeug) should only be used in a development environment
    # On production you could run it through uWSGI,
    # optionally with a webserver like nginx or apache in front of that
    # uWSGI can also quite easily be started with ssl,
    # which the IXON Cloud requires for webhooks for security reasons
    if args.webhook:
        flask_app = create_app()
        flask_app.run(host="0.0.0.0", port=int(args.port), debug=args.debug)
