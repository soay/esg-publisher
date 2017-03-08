""""Handle CMIP6 data file metadata"""

import os
import re

from cmip5_product import getProduct

from esgcet.exceptions import *
from esgcet.config import BasicHandler, getConfig, compareLibVersions, splitRecord
from esgcet.messaging import debug, info, warning, error, critical, exception

import numpy
import argparse
import imp

WARN = False

PrePARE_PATH = '/usr/local/conda/envs/esgf-pub/bin/PrePARE.py'

version_pattern = re.compile('20\d{2}[0,1]\d[0-3]\d')

class CMIP6Handler(BasicHandler):

    def __init__(self, name, path, Session, validate=True, offline=False):

        self.validator = None

        BasicHandler.__init__(self, name, path, Session, validate=validate, offline=offline)



    def openPath(self, path):
        """Open a sample path, returning a project-specific file object,
        (e.g., a netCDF file object or vanilla file object)."""
        fileobj = BasicHandler.openPath(self, path)
        fileobj.path = path
        return fileobj


    def validateFile(self, fileobj):
        """Raise ESGInvalidMetadataFormat if the file cannot be processed by this handler."""
        pass

    def check_pid_avail(self, project_config_section, config, version=None):
        """ Returns the pid_prefix

         project_config_section
            The name of the project config section in esg.ini

        config
            The configuration (ini files)

        version
            Integer or Dict with dataset versions
        """
        # disable PIDs for local index without versioning (IPSL use case)
        if isinstance(version, int) and not version_pattern.match(str(version)):
            warning('Version %s, skipping PID generation.' % version)
            return None

        return '21.14100'

    def get_pid_config(self, project_config_section, config):
        """ Returns the project specific pid config

         project_config_section
            The name of the project config section in esg.ini

        config
            The configuration (ini files)
        """
        # get the PID configs
        pid_messaging_service_exchange_name = 'esgffed-exchange'

        # get credentials from config:project section of esg.ini
        if config.has_section(project_config_section):
            pid_messaging_service_credentials = []
            credentials = splitRecord(config.get(project_config_section, 'pid_credentials', default=''))
            if credentials:
                priority = 0
                for cred in credentials:
                    if len(cred) == 4 and isinstance(cred[3], int):
                        priority = cred[3]
                    elif len(cred) == 3:
                        priority += 1
                    else:
                        raise ESGPublishError("Misconfiguration: 'pid_credentials', section '%s' of esg.ini." % project_config_section)
                    pid_messaging_service_credentials.append({'url': cred[0], 'user': cred[1], 'password': cred[2], 'priority': priority})
            else:
                raise ESGPublishError("Option 'pid_credentials' missing in section '%s' of esg.ini. "
                                      "Please contact your tier1 data node admin to get the proper values." % project_config_section)
        else:
            raise ESGPublishError("Section '%s' not found in esg.ini." % project_config_section)

        return pid_messaging_service_exchange_name, pid_messaging_service_credentials

    def get_citation_url(self, project_section, config, dataset_name, dataset_version):
        """ Returns the citation_url if a project uses citation, otherwise returns None

         project_section
            The name of the project section in the ini file

        config
            The configuration (ini files)

        dataset_name
            Name of the dataset

        dataset_version
            Version of the dataset
        """
        return 'http://cera-www.dkrz.de/WDCC/meta/CMIP6/%s.v%s.json' % (dataset_name, dataset_version)
