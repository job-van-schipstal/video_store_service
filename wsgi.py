"""
Entrypoint for running this module with uWSGI(or similar) and thus a webserver in front of flask
If you want to test locally, or use the CLI, call:
 python -m video_store_service (--help)

More information on using uWSGI and a webserver with a project like this can be found here:
https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-14-04
"""
from video_store_service import __main__

if __name__ == '__main__':
    app = __main__.create_app()
    app.run()
