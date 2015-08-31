"""Module for dealing with program configuration data.
   Config data can come from two places:
   - The command line
   - a YAML configuration file

This module provides a consistent means of accessing/saving configuration settings.

Only YAML files are currently supported.
Only reading config values is currently supported.
"""

#Notes:
#    1 - Comments and code style follows "Style Guide For Python Code"

# Standard Library Imports
import argparse
import logging

# Third Party Imports
import yaml

#Local Application/Library Specific Imports
from NestedDict import NestedDict

class config(NestedDict):
    """Class to deal with program configuration settings

       Configuration setting are taken from two locations:
       - the command line
       - a YAML configuration file

       By default the config file used is ./config.yml.
       The default can be overridden on the command line using -f.
       """

    def __init__(self, parser=None, *args):
        """create an instance of this class
        """
        NestedDict.__init__(self)
        
        logging.basicConfig(
            format='%(levelname) -10s (%(threadName)-10s) %(asctime)s %(module)s:%(funcName)s[%(lineno)s] %(message)s')
        self.logger = self.setLogging(self.__class__.__name__)

        if (parser == None ):
            parser = argparse.ArgumentParser ()

        parser.add_argument('-f', action='store', dest='file',
                            default='./config.yml',
                            help='Load config file in YAML format. "./config.yml" used by default')
        self.results = parser.parse_args()

        try:
            self.logger.info ("Using config file %s", self.results.file)
            f = open(self.results.file)

            with f:
                data = yaml.safe_load(f)     # use safe_load instead of load
                #print 'data ' + yaml.dump(data)

                # copy dict values from YAML file over to nested dictionary
                self.copy_recursive(data, self)

        except IOError:
            self.logger.warning ("No YAML config file was found. (Looked for '%s' ... use '-f' on command line to change this)", self.results.file)
        except:
            self.logger.error ("YAML config file not parsed successfully (improperly formatted?).")
            raise


    def dump (self):
        """Return the config data as a readable string."""

        results = self.results
        self.results = ""
        res = yaml.dump(self)
        self.results = results

        return res

    def setLogging (self, _class = None):
        """Set final logging level based on contents of config file"""

        _logger = logging.getLogger(_class)

        if _class == None:
            logging.basicConfig(
                format='%(levelname) (%(threadName)-10s) -10s %(asctime)s %(module)s:%(funcName)s[%(lineno)s] %(message)s')
            _class = "logging"
        else:
            _class = "logging." + _class


        _logger.setLevel(getattr(logging, self.get(_class + ".level", "INFO", True).upper()))
        self.setdefault(_class + ".logger", _logger)

        #self.logger.debug("Config File contents => %s", self.dump())

        return _logger

if __name__ == '__main__':

    logging.basicConfig(format='%(levelname) -10s (%(threadName)-10s) %(asctime)s %(module)s:%(funcName)s[%(lineno)s] %(message)s',
                            level="DEBUG")

    cfg = config()
    cfg.setLogging()
    
    logging.info("Config file contents: %s", cfg.dump())

    cfg["XXX"] = "test1"
    cfg["YYY.test2"] = "a"
    cfg["QQQ.test3.a"] = "b"
    cfg["RRR.test3"] = "b"
    cfg["RRR.test4.a"] = "c"

    logging.info("Config file contents: %s", cfg.dump())
