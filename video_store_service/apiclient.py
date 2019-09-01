"""
Client for the IXON api
Responsible for discovering the api
Authenticating and getting the webaccess url
And establishing the data stream to be piped to ffmpeg
"""

import requests, re, logging
from base64 import b64encode
from typing import Dict, Any
from requests.auth import HTTPDigestAuth


def get_auth_string(credentials: str) -> str:
    """
    Makes authstring from credentials: Basic {base64 encoded user:password}
    """
    return f'Basic {b64encode(bytes(credentials, "utf-8")).decode()}'


class Client():
    """
    Class that handles connection to the IP camera through the IXON cloud
    """
    # Entrypoint URL
    url = 'https://api.ixon.net:443/'

    # Static api config
    expires_in = 60  # 1H
    timeout = 10  # Wait 10 sec for response, at most

    def __init__(self, ixapi_config: Dict[str, Any]):
        """
        Store config and create base headers Dict
        :param ixapi_config: Dict with IXapi config options
        """
        # Check that we have an API Key
        if ixapi_config.get('api_key', '') == '':
            print('program cannot work: NO API KEY')
            return

        # Generate base headers
        self.__ixapi_config = ixapi_config
        self.__base_headers: Dict[str, Any] = {
            "Accept": "application/json",
            "IXapi-Application": ixapi_config.get('api_key', ''),
            "IXapi-Version": "1",
        }

        # Do discovery
        discovery = requests.get(self.url, headers=self.__base_headers, timeout=self.timeout)
        if not discovery.status_code == 200:
            raise ValueError(f'Api Discovery Failed, status code: {discovery.status_code}')
        self.__links = discovery.json().get('links')


    def getURL(self, rel: str) -> str:
        """
        Gets URL from discovery belonging to the specified rel
        :param rel: name of link you looking for
        :return: URL from discovery that matched, ValueError if none was found
        """
        for link in self.__links:
            if link.get('rel') == rel:
                return link.get('href')
        raise ValueError(f'The rel {rel} was not found')

    def get_auth_header(self, company_id: str = None) -> Dict[str, str]:
        """
        Authenticates to the IXON api and generates full header
        :param company_id: Optional: ID of the company the camera is in
        :return: full_header with authorization and company_id if defined
        """
        # create login header
        login_header = self.__base_headers.copy()
        login_header['Authorization'] = get_auth_string(
            f'{self.__ixapi_config.get("email", "")}::{self.__ixapi_config.get("password", "")}')

        # Request token
        login = requests.post(self.getURL('AccessTokenList'),
                              headers=login_header,
                              timeout=self.timeout,
                              params={"fields": "secretId"},
                              json={'expiresIn': self.expires_in})
        if login.status_code == 201 and login.json().get('status') == 'success':
            secret_id = login.json().get('data').get('secretId')
        else:
            raise ValueError('Did not recieve accessToken from api, status code: '
                             f'{login.status_code}, response: {login.content}')

        # create authorized header
        full_header: Dict[str, str] = self.__base_headers.copy()
        full_header['Authorization'] = f'Bearer {secret_id}'
        if company_id is not None:
            full_header['IXapi-Company'] = company_id
        return full_header

    def get_webaccess_connection(self, camera_config: Dict[str, Any]) \
            -> requests.Response:
        """
        Calls get_auth_header() to get auth
        Gets Webaccess url
        Connects to webacccess url to get cookie
        connects to webaccess url to get video stream

        :param camera_config: class containing webhook-specific camera settings
        :return: Response object, contains videostream
        """
        ### get webaccess url ###
        request = requests.post(self.getURL('WebAccessList'),
                                headers=self.get_auth_header(camera_config.get('company_id', '')),
                                timeout=self.timeout,
                                json={'method': camera_config.get('webaccess_access_type', ''),
                                      'server':
                                          {'publicId': camera_config.get('webaccess_service_id', '')
                                           }})
        if not request.status_code == 201 or not request.json().get('status') == 'success':
            raise ValueError('WebAccess request was not successfull, status code: '
                             f'{request.status_code}, response: {request.content}')
        server_url = request.json()['data']['url']

        ### Connect to IP Camera ###
        # First connect to authorize ourselves to the IXON Cloud & recieve a cookie
        # Do not redirect, we only want to talk to the platform, not the webserver from the camera
        session = requests.Session()
        session.get(server_url, allow_redirects=False)

        # Now we no longer need the ?auth=XXXXXX part
        result: Any = re.search('(.+?)\?auth', server_url)
        base_url = result.group(1)

        stream_url = camera_config.get('stream_path', '')
        if stream_url.startswith('/'):
            stream_url = stream_url[1:]
        url = f'{base_url}{stream_url}'
        logging.debug('HTTP ACCESS URL: %s', url)
        access = None
        kwargs = {
            'allow_redirects': True,
            'stream': True,
            'timeout': self.timeout
        }
        if 'auth' in camera_config and not camera_config['auth'].get('type', 'none') == 'none':
            # Case: http-basic
            if camera_config['auth'].get('type', '') == 'basic':
                access = session.get(url,
                                     auth=(camera_config["auth"].get("username", ""),
                                           camera_config["auth"].get("password", "")),
                                     **kwargs)
            # Case: http-digest
            elif camera_config['auth'].get('type', '') == 'digest':
                access = session.get(url,
                                     auth=HTTPDigestAuth(
                                         camera_config["auth"].get("username", ""),
                                         camera_config["auth"].get("password", "")),
                                     **kwargs)
            # Case: unsupported / typo
            else:
                raise ValueError('Unkown Authentication method in config file')
        # Case: no Auth
        else:
            access = session.get(url, **kwargs)

        if not access.status_code == 200:
            raise ValueError('Recieved status code: {access.status_code}')
        return access
