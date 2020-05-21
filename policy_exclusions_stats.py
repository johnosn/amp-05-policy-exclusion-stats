# -*- coding: utf-8 -*-

"""
Script to count the number of process exclusions per policy.

Description
-----------
    This script:
     1.) Connects to the Cisco AMP for Endpoints API.
     2.) Enumberates all of the policies in the environment.
     3.) Downloads a copy of the policy.xml file for each policy and stores
         it in the "output" "policy_files" folder.
     4.) Evaluates the exclusions for each policy.
     5.) Creates tables with the number of file and policy exclusions for
         each policy.
     6.) Stores the tables in csv format to the "output" folder.
     7.) Generates a Caution and Warning message for policies that have a
         large number of process exclusions.

Configure
---------
    To use the script:
     1.) Configure the "api.cfg" file in the "config" folder with your AMP
         API client ID.
     2.) Create credential in Windows "Credential Manager"
          a.) Under "Windows Credentials" click "Add a generic credential".
          b.) For "Internet or network address:" enter "AMP".
          c.) For "User name:" enter the AMP API client ID
          d.) For "Password:" enter the AMP API client secret

File Output
-----------
    Policy.xml Files:
        Policy.xml files are stored as <policy_name>.xml in the "policy_files"
        folder within the "output" folder.

    Path_exculsions.csv File:
        The count of path exclusions by policy name can be found in the
        "path_exclusions.csv" file within the "output" folder.

    Process_exclusions.csv File:
        The count of process exclusions by policy name can be found in the
        "process_exclusions.csv" file within the "output" folder. This output
        file includes the number of process exclusions that apply to all
        child processes.

Screen Output
-------------
    The script outputs:
        File exclusion count for policy by type
            <table>
        Process exclusion types by policy
            <table>
        CAUTION: Policy has close to the maximum of 100 process exceptions.
                 <policy_name> has <number> exceptions

        WARNING: Policy exceeds the maximum 100 process exceptions.
                 <policy_name> has <number> exceptions
"""

import configparser
import logging
from logging.config import fileConfig
import xml.etree.ElementTree as ET
import concurrent.futures
import requests
import keyring
import pandas as pd
from tabulate import tabulate
import numpy as np


class AMP4EP():
    """AMP4EP class.

    Attributes
    ----------
        cfg_file:   Configuration file path
        client_id:  Cisco AMP for ENdpoint API Client ID
        limit:      Number of policies to return
        url:        Cisco AMP for Endpoints API address
        clt_pwd:    Cisco AMP for Endpoints API password
        session:    Request dession to the AMP API
    """

    ### Set the config file path
    cfg_file = r'.\config\api.cfg'

    ### Read the config file
    config = configparser.ConfigParser()
    config.read(cfg_file)

    ### Parse settings from config file and assign to class attributes
    clt_id = config.get('AMP', 'amp_client_id')
    limit = config.get('AMP', 'limit')
    url = config.get('AMP', 'amp_host')

    ### Get password from the keyring
    clt_pwd = keyring.get_password("AMP", clt_id)

    ### Create AMP session
    session = requests.session()
    session.auth = (clt_id, clt_pwd)

    @classmethod
    def get_policy_list(cls):
        """
        Get list of policies.

        Parameters
        ----------
        None.

        Returns
        -------
        polices : Object
            A list of policies.

        """
        LOG.debug('Attempting to get policy list')

        url = "{0}policies?limit={1}".format(cls.url, cls.limit)
        headers = {'Content-Type': 'application/json'}
        response = cls.session.get(url, headers=headers)
        HttpResp.status(response, url)
        policies = response.json()

        p_count = str(len(policies['data']))
        LOG.info('Retrieved list of %s policies', p_count)

        return policies['data']

    @classmethod
    def get_policy(cls, policy):
        """
        Get policy xml data.

        Parameters
        ----------
        policy : Objects
            Specific policy to get xml data for.

        Returns
        -------
        policy_detail : Object
            A list of computer guids to move.

        <policy_name>.xml : file
            Policy XML file used by AMP4EP.

        """
        # Set Policy Data
        p_name = policy['name']
        p_link = policy['links']['policy']
        LOG.debug('Attempting to get details for \"%s\"', p_name)

        # Get data from AMP API
        url = "{0}.xml".format(p_link)
        response = cls.session.get(url)
        HttpResp.status(response, p_name)

        # Write policy.xml file to output folder
        LOG.debug('Attempting to write policy.xml for \"%s\"', p_name)
        file_out = '.\\output\\policy_files\\' + p_name + '.xml'
        with open(file_out, 'w') as file:
            file.write(response.text)

        # Parse XML results
        doc = ET.fromstring(response.content)
        tree = ET.ElementTree(doc)
        root = tree.getroot()

        return root

    @classmethod
    def parse_path_exclusions(cls, policy, xml):
        """
        Get policy xml data.

        Parameters
        ----------
        policy : Object
            Specific policy metadata.
        xml : Object
            Specific policy data stored in the policy xml file.

        Returns
        -------
        e_paths : Dataframe
            A list of path exclusions found in policies.

        """
        # Create Variables
        e_paths = pd.DataFrame()

        # Set policy data
        p_name = policy['name']
        p_guid = policy['guid']

        # Find Exclusions
        LOG.debug('Attempting to find path exclusions for \"%s\"', p_name)

        # Get Exclusions
        for xml_exclusion in xml.iter('{http://www.w3.org/2000/09/xmldsig#}exclusions'):

            # Get Path Exclusions
            for xml_path in xml_exclusion.iter('{http://www.w3.org/2000/09/xmldsig#}info'):
                for xml_item in xml_path:
                    e_class = 'path'
                    exclusion = xml_item.text.split("|")
                    e_item = {'p_name': p_name,
                              'p_guid': p_guid,
                              'e_class': e_class,
                              'e_type': exclusion[1],
                              'e_value': exclusion[4]}
                    e_paths = e_paths.append(e_item, ignore_index=True)
        return e_paths

    @classmethod
    def parse_process_exclusions(cls, policy, xml):
        """
        Get policy xml data.

        Parameters
        ----------
        policy : Object
            Specific policy metadata.
        xml : Object
            Specific policy data stored in the policy xml file.

        Returns
        -------
        e_processes : Dataframe
            A list of process exclusions found in policies.

        """
        # Create Variables
        e_processes = pd.DataFrame()

        # Set policy data
        p_name = policy['name']
        p_guid = policy['guid']

        # Find Exclusions
        LOG.debug('Attempting to find process exclusions for \"%s\"', p_name)

        # Get Process Exclusions
        for xml_exclusion in xml.iter('{http://www.w3.org/2000/09/xmldsig#}exclusions'):
            for xml_process in xml_exclusion.iter('{http://www.w3.org/2000/09/xmldsig#}process'):
                for xml_item in xml_process:
                    e_class = 'process'
                    exclusion = xml_item.text.split("|")
                    e_flag = int(exclusion[4])
                    e_item = {'Policy Name': p_name,
                              'Policy GUID': p_guid,
                              'Polcy Class': e_class,
                              'Exclusion Version': exclusion[0],
                              'Exclusion Auth Type': exclusion[1],
                              'Exclusion Hash': exclusion[2],
                              'Exclusion Path': exclusion[3],
                              'Exclusion Flag': int(e_flag),
                              'File Scan Child': bool(e_flag & (0b1 << 0)),
                              'Scan Files Written': bool(e_flag & (0b1 << 1)),
                              'System Process Protection': bool(e_flag & (0b1 << 2)),
                              'System Process Protection Child': bool(e_flag & (0b1 << 3)),
                              'Malicious Activity': bool(e_flag & (0b1 << 4)),
                              'Malicious Activity Child': bool(e_flag & (0b1 << 5)),
                              'Self Protect': bool(e_flag & (0b1 << 6)),
                              'Self Protect Child': bool(e_flag & (0b1 << 7))}
                    e_processes = e_processes.append(e_item, ignore_index=True)
        return e_processes

    @classmethod
    def exclusion_report(cls, path, process):
        """
        Get policy xml data.

        Parameters
        ----------
        path : Dataframe
            Dataframe of path exclusions
        process : Dataframe
            Datafrome of process exclusions.

        Returns
        -------
        None.

        """
        # Set Pandas display parameters
        pd.options.display.max_columns = None
        pd.options.display.width = None

        # Cross Tabulate Path Exclusions
        LOG.debug('Creating Path Exclusion Summary')
        path_exc = pd.crosstab(path.p_name,
                               path.e_type,
                               rownames=['Policy Name'],
                               margins=True,
                               margins_name='Total Exclusions')
        path_exc = path_exc.rename(columns={'1': 'Threat',
                                            '2': 'Path',
                                            '3': 'File Extension',
                                            '4': 'File Name',
                                            '5': 'Process',
                                            '6': 'Wildcard'})
        path_exc = path_exc.drop(path_exc.index[len(path_exc) - 1])

        # Calculate Process Exclusions
        LOG.debug('Creating Process Exclusion Summary')
        process['File Scan'] = process['Exclusion Flag'].apply(lambda x: x in range(0, 3), True)
        pvt_process = pd.pivot_table(process,
                                     values=['Policy GUID',
                                             'File Scan',
                                             'File Scan Child',
                                             'System Process Protection',
                                             'System Process Protection Child',
                                             'Malicious Activity',
                                             'Malicious Activity Child'],
                                     index='Policy Name',
                                     aggfunc={'Policy GUID': len,
                                              'File Scan': np.sum,
                                              'File Scan Child': np.sum,
                                              'System Process Protection': np.sum,
                                              'System Process Protection Child': np.sum,
                                              'Malicious Activity': np.sum,
                                              'Malicious Activity Child': np.sum},
                                     fill_value=0)
        pvt_process = pvt_process.rename(columns={'Policy GUID': 'Total Exclusions'})
        pvt_process = pvt_process[['File Scan', 'File Scan Child', 'System Process Protection',
                                   'System Process Protection Child', 'Malicious Activity',
                                   'Malicious Activity Child', 'Total Exclusions']]

        # Caution level policies
        LOG.debug('Find policies with 90 - 100 Process Exclusions')
        caution_list = pd.DataFrame()
        for index, row in pvt_process.iterrows():
            if row['Total Exclusions'] in range(90, 101):
                caution = {'Policy Name': index,
                           'Total Exclusions': row['Total Exclusions']}
                caution_list = caution_list.append(caution, ignore_index=True)

        # Warning level policies
        LOG.debug('Find policies with over 100 Process Exclusions')
        warning_list = pd.DataFrame()
        for index, row in pvt_process.iterrows():
            if row['Total Exclusions'] > 100:
                warning = {'Policy Name': index,
                           'Total Exclusions': row['Total Exclusions']}
                warning_list = warning_list.append(warning, ignore_index=True)

        # Save results to file
        LOG.debug('Saving exclusion summary files to the output folder')
        path_exc.to_csv(r'.\output\path_exclusions.csv', index=True)
        pvt_process.to_csv(r'.\output\process_exclusions.csv', index=True)

        # Print Results
        LOG.debug('Printing Results')
        print('Path exclusion count for policy by type')
        print(tabulate(path_exc, headers='keys', tablefmt="psql"))
        print()

        pvt_process = pvt_process.drop(columns=['File Scan Child',
                                                'System Process Protection Child',
                                                'Malicious Activity Child'])

        pvt_process = pvt_process.rename(columns={'File Scan': 'FS',
                                                  'System Process Protection': 'SPP',
                                                  'Malicious Activity': 'MA'})

        print('Process exclusion types by policy')
        print(tabulate(pvt_process, headers='keys', tablefmt="psql"))
        print('    FS = File Scan')
        print('    SPP = System Process Protection')
        print('    MA = Malicious Activity')
        print()

        if len(caution_list) > 0:
            print('CAUTION: Policy has close to the maximum of 100 process exceptions.')
            for index, row in caution_list.iterrows():
                print('         \"{0}\" has {1} exceptions'.format(row['Policy Name'],
                                                                   int(row['Total Exclusions'])))
            print()

        if len(warning_list) > 0:
            print('WARNING: Policy exceeds the maximum 100 process exceptions.')
            for index, row in warning_list.iterrows():
                print('         \"{0}\" has {1} exceptions'.format(row['Policy Name'],
                                                                   int(row['Total Exclusions'])))
            print()


class HttpResp:
    """Test HTTP response to determine success/failure."""

    @staticmethod
    def status(response, query):
        """
        Check if a HTTP 200 response was received from the server, quit if not.

        Parameters
        ----------
        response : String
            HTTP response data.
        query : String
            Something that was requested

        Returns
        -------
        None.

        """
        ### Set logging references
        mthd = 'HTTPRESPONSE.STATUS:'

        ### Create log message
        code = response.status_code
        reason = response.reason
        log_msg = "{0} Found HTTP {1} {2} for {3}".format(mthd, code, reason, query)

        ### Check if success
        if response.status_code // 100 != 2:

            ### Log error
            LOG.error(log_msg)

        else:
            LOG.debug(log_msg)


def main():
    """Call class functions."""
    LOG.info('Script initiated')

    # Create dataframes to store exclusions
    df_paths = pd.DataFrame([])
    df_processes = pd.DataFrame([])

    # Get Policy List
    policies = AMP4EP.get_policy_list()

    # Multi threaded policy collection and evaluationa
    LOG.info('Starting multi-threaded policy collection and evaluation')
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_get_policy = {executor.submit(AMP4EP.get_policy,
                                             policy): policy for policy in policies}

        for future in concurrent.futures.as_completed(future_get_policy):
            policy = future_get_policy[future]
            policy_xml = future.result()

            p_paths = executor.submit(AMP4EP.parse_path_exclusions, policy, policy_xml)
            if p_paths.result() is not None:
                df_paths = df_paths.append(p_paths.result(), ignore_index=True)

            # Get Process Exclusions
            p_processes = executor.submit(AMP4EP.parse_process_exclusions, policy, policy_xml)
            if p_processes.result() is not None:
                df_processes = df_processes.append(p_processes.result(), ignore_index=True)
    LOG.info('Completed multi-threaded policy collection and evaluation')

    # Review Exclusions
    AMP4EP.exclusion_report(df_paths, df_processes)

    # Stop logging events
    LOG.info('Script completed')


if __name__ == "__main__":

    ### Setup Logging
    fileConfig(r'.\config\logging.cfg',
               defaults={'logfilename': r'.\logs\script.log'})
    LOG = logging.getLogger('script_logger')
    LOG.setLevel(logging.DEBUG)

    ### Start Main
    main()
