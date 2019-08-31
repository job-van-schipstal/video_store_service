"""
This is a simple utility to help you find the right webaccess service id
It is also, in combination with the apiclient,
a simple example of how you can use the IXON api
"""

import sys, requests, yaml
from typing import Dict, Any

from video_store_service import apiclient


def get_user_choice(response: Dict[Any, Any]) -> str:
    """
    Simple utility function to display a list op options,
    and let the user pick one by using the index (displayed in front of it)
    :param response: Dict with the response recieved from the IXON api
    :return: str PublicID of chosen index
    """
    options = list()

    # Add them to a list
    for option in response['data']:
        options.append(option)

    # Display list
    for i in range(len(options)):
        option = options[i]
        public_id = option['publicId']
        name = option['name']
        print(f'{i}: {public_id}, {name}')

    # Make user pick one
    index: int = int(input('enter an index: '))  # will throw ValueError if not int, not a problem
    if not 0 <= index < len(options):
        raise ValueError(f'{index} is not a valid choice')
    return options[index]['publicId']


def run_configuration_utility(config: Dict[str, Any], client: apiclient.Client):
    """
    This is a very basic wizard that first uses the apiclient to login
    Then it lists the companies and asks the user to pick one
    Then it does the same for devices and finally for webaccess
    :param config: Dict with configuration options
    :param client: Instance of IXON apiclient
    :return: nothing
    """
    credentials = config['IXON_api']
    if credentials.get('api_key', '') == '' \
            or credentials.get('email', '') == '' \
            or credentials.get('password', '') == '':
        print('First set api_key, email and password in config')
        return

    # Get header with auth token from apiclient
    auth_header = client.get_auth_header()

    # Request: Get company list
    companies = requests.get(client.getURL('CompanyList'), headers=auth_header)
    if companies.status_code != 200:
        print(f'Recieved invalid status_code: {companies.status_code}')
    reply = companies.json()
    if not reply or reply['status'] != 'success':
        print(f'invalid reply: {companies.content}')

    # Get user choice
    print('= Select Company, enter the index in front of it')
    company = get_user_choice(reply)

    # Add it to the config
    config['camera']['company_id'] = company

    # Add company to header for next request
    auth_header['IXapi-Company'] = company

    # Request: Get devices in company
    device_list = requests.get(client.getURL('AgentList'), headers=auth_header)
    if not device_list.status_code == 200 or not device_list.json().get('status') == 'success':
        raise ValueError(
            'Invalid response: status code: '
            f'{device_list.status_code}, response: {device_list.content}')

    # Get user choice
    print('= Select Device, enter the index in front of it')
    agent_id = get_user_choice(device_list.json())

    # Request: Get services on device
    agent_list = requests.get(client.getURL('AgentServerList').replace('{agentId}', agent_id),
                              headers=auth_header)
    if not device_list.status_code == 200 or not device_list.json().get('status') == 'success':
        raise ValueError(
            'Invalid response: status code: '
            f'{device_list.status_code}, response: {device_list.content}')

    # Get user choice
    print('= Select Webaccess service, enter the index in front of it')
    webaccess = get_user_choice(agent_list.json())

    # Add it to the config
    config['camera']['webaccess_service_id'] = webaccess

    print('Finished')
    print(f'You have selected: company_id: {company}, webaccess_service_id: {webaccess}')
    choice = input('Save these in config? (removes comments, manual may be preferred) (y/n) ')
    if choice in ('y', 'Y', 'yes', 'Yes'):
        with open('config.yml', 'w') as config_file:
            yaml.dump(config, config_file, default_flow_style=False)
        print('Saved values')
    else:
        print('Values were not saved, retry or type them in manually')
    print('You will still have to configure, if you haven\'t already:')
    print('- The http, access method: http, or https')
    print('- The login credentials, if required')
    print('- The path to the actual video stream, '
          'can be found using google chrome developer tools, for example')
    sys.exit(1)
