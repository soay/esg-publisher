""""Handle CMIP6 data file metadata"""

import os
import re
import urlparse

from cmip5_product import getProduct

from esgcet.exceptions import *
from esgcet.config import BasicHandler, getConfig, compareLibVersions
from esgcet.messaging import debug, info, warning, error, critical, exception

import numpy

from cmip6_cv.CMIP6Validator import JSONAction, CDMSAction, checkCMIP6
import argparse


WARN = False

from cfchecker import *

version_pattern = re.compile('20\d{2}[0,1]\d[0-3]\d')

cmorAttributes = {
    'time_frequency': 'frequency',
    }

class CMIP6Handler(BasicHandler):

    def __init__(self, name, path, Session, validate=True, offline=False):

        BasicHandler.__init__(self, name, path, Session, validate=validate, offline=offline)


    def openPath(self, path):
        """Open a sample path, returning a project-specific file object,
        (e.g., a netCDF file object or vanilla file object)."""
        fileobj = BasicHandler.openPath(self, path)
        fileobj.path = path
        return fileobj


    def readContext(self, cdfile, model=''):
        """Get a dictionary of keys from an open file"""
        result = BasicHandler.readContext(self, cdfile)
        f = cdfile.file

        for key, value in cmorAttributes.items():
            try:
                result[key] = getattr(f, value)
            except:
                pass
        return result


    def validateFile(self, fileobj):
        """Raise ESGInvalidMetadataFormat if the file cannot be processed by this handler."""
        
        f = fileobj.path

        config = getConfig()
        projectSection = 'project:'+self.name


        min_cmor_version = config.get(projectSection, "min_cmor_version", default="0.0.0")

        file_cmor_version = fileobj.getAttribute('cmor_version', None)
        
        if compareLibVersions(min_cmor_version, file_cmor_version):
            debug('File %s cmor-ized at version %s, passed!"'%(f, file_cmor_version))
            return


        min_cf_version = config.get(projectSection, "min_cf_version", defaut="")        



        if len(min_cf_version) == 0: 
            raise ESGPublishError("Minimum CF version not set in esg.ini")

        fakeversion = ["cfchecker.py", "-v", "1.0", "foo"]
        
        (badc,coards,uploader,useFileName,standardName,areaTypes,udunitsDat,version,files)=getargs(fakeversion)


        CF_Chk_obj = CFChecker(uploader=uploader, useFileName=useFileName, badc=badc, coards=coards, cfStandardNamesXML=standardName, cfAreaTypesXML=areaTypes, udunitsDat=udunitsDat, version=version)

        rc = CF_Chk_obj.checker(f)

        if (rc > 0):
            raise ESGPublishError("File %s fails CF check"%f)


        table = None

        try:
            table = fileobj.getAttribute('table_id', None)

        except:
            raise ESGPublishError("File %s missing required table_id global attribute"%f)


        cmor_table_path = config.get(projectSection, "cmor_table_path", defaut="")        


        if cmor_table_path == "":
            raise ESGPublishError("cmor_table_path not set in esg.ini")            

        table_file = cmor_table_path + '/CMIP6_' + table + '.json'


        fakeargs = [ table_file ,f]

        parser = argparse.ArgumentParser(prog='esgpublisher')
        parser.add_argument('cmip6_table', action=JSONAction)
        parser.add_argument('infile', action=CDMSAction)

        args = parser.parse_args(fakeargs)


#        print "About to CV check:", f
 
        try:
            process = checkCMIP6(args)
            if process is None:
                raise ESGPublishError("File %s failed the CV check - object create failure"%f)

            process.ControlVocab()


        except:

            raise ESGPublishError("File %s failed the CV check"%f)


    def check_pid_avail(self, project_config_section, config, version=None):
        """ Returns the pid_prefix

         project_config_section
            The name of the project config section in esg.ini

        config
            The configuration (ini files)

        version
            Integer or Dict with dataset versions
        """
        # disable PIDs for local index that does not use versioning (IPSL use case)
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
        pid_ms_exchange_name = 'esgffed-exchange'

        # extract credentials from config:project section of esg.ini
        if config.has_section(project_config_section):
            pid_messaging_service_credentials = []
            credentials = splitRecord(config.get(project_config_section, 'pid_messaging_service_credentials', default=None))
            if credentials:
                priority = 0
                for cred in credentials:
                    if len(cred) == 4 and isinstance(cred[3], int):
                        priority = cred[3]
                    else:
                        priority += 1
                        pid_messaging_service_credentials.append({'url': cred[0], 'user': cred[1], 'password': cred[2], 'priority': priority})
            else:
                raise ESGPublishError("Option 'pid_messaging_service_credentials' missing in section '%s' of esg.ini. "
                       "Please contact your tier1 data node admin to get the proper values." % section)
        else:
            raise ESGPublishError("Section '%s' was not found in esg.ini." % project_config_section)

        return pid_ms_exchange_name, pid_messaging_service_credentials


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
