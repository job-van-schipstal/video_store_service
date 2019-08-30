# Video Store Service
### Capture video’s if something goes wrong, and store it in the cloud!


Imagine you have a packaging robot that appears to randomly have errors once in a while. It would switch into an alarm state, which the platform would know since you configured an alarm on it. You are notified, but you're still not sure what went wrong and how to resolve it. 

With that in mind, I created the Video Store Service, as proof on concept. It works like this:

You configure the IXON Cloud to raise a webhook in response to Cloud Notify. 
When the Video Store Service receives this webhook, it logs into the IXON api and connects to your IP Camera through the IXON Cloud. 
Now it records a clip using ffmpeg (an open source video capturer/recorder and much more)  and stores it.

Looking back at these clips, patterns could be found in when the error occurs and you’ll have a better chance to fix it.

This service was written in just a few days and is available for you to try and experiment with under the <b>MIT license</b>.<br>
The IXON api provides advanced functionality but remains easy to use and quick to implement. 

Many of these kinds of little projects can quickly be built!



## Installation

This project requires ffmpeg which you can download here (recent version recommended):
https://ffmpeg.org/download.html

This project was written in python(3), so that is required as well, install it using your package manager or, if you’re on windows, get it here:
https://www.python.org/downloads/


Then clone the repository:

```$ git clone https://github.com/job-van-schipstal/video_store_service.git```

now open the directory and install the last of the dependencies using pip:

```$ pip install -r requirements.txt```

## Configuration:

Configuration happens through the config.yaml file
<details>
<summary>View full file</summary>
<br>
<b>General IXON api settings</b><br>
IXON_api:<br>
 -api_key: Can be requested from support<br>
 -email: Your email<br>
 -password: Your password<br>
<br>
<b>Camera settings</b><br>
camera:<br>
  -auth:<br>
    --type: Auth type, options: none, basic, digest<br>
    --password: Camera's Password<br>
    --username: Camera's username<br>
  -company_id: Camera's company ID<br>
 -webaccess_service_id: Can be found using the configuration utility, run main.py -c<br>
 -webaccess_access_type: http or https<br>
 -stream_path: Path on the camera to the actual video stream<br>
<br>
<b>Recording settings</b><br>
video:<br>
 -debug_info: true:  let FFMPEG display lots of video information, best to disable after testing<br>
 -duration: 10:      Duration of the recording in seconds<br>
 -framerate: 10:     If framerate is not detected properly automaticaly, set it here, else: 'auto'<br>
 -recode: true:      Should we recode to h264? CPU heavy but required for certain streams<br>
<br>
<b>Webhook settings</b><br>
webhooks:<br>
 -queue_size: 10:    Maximum amount of webhook calls that can be waiting to be recorded<br>
</details>

## License

The Video Store Service is licensed under the [MIT License](LICENSE).
