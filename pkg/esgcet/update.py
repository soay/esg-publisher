from esgcet.pub_client import publisherClient
import sys, json, requests
from esgcet.settings import INDEX_NODE, CERT_FN
import configparser as cfg
from datetime import datetime
from pathlib import Path

config = cfg.ConfigParser()
home = str(Path.home())
config_file = home + "/.esg/esg.ini"
config.read(config_file)

try:
    s = config['user']['silent']
    if 'true' or 'yes' in s:
        SILENT = True
    else:
        SILENT = False
except:
    SILENT = False
try:
    v = config['user']['verbose']
    if 'true' or 'yes' in v:
        VERBOSE = True
    else:
        VERBOSE = False
except:
    VERBOSE = False

ARGS = 1

SEARCH_TEMPLATE = 'http://{}/esg-search/search/?latest=true&distrib=false&format=application%2Fsolr%2Bjson&data_node={}&master_id={}&fields=version,id'

''' The xml to hide the previous version
'''
def gen_hide_xml(id, *args):

    dateFormat = "%Y-%m-%dT%H:%M:%SZ"
    now = datetime.utcnow()
    ts = now.strftime(dateFormat)
    txt =  """<updates core="datasets" action="set">
        <update>
          <query>id={}</query>
          <field name="latest">
             <value>false</value>
          </field>
          <field name="_timestamp">
             <value>{}</value>
          </field>
        </update>
    </updates>
    \n""".format(id, ts)

    return txt

def run(args):

    if len(args) < 1:
        print("usage: esgupdate <JSON file with dataset output>", file=sys.stderr)
        exit(1)
    try:
        if len(args) == 1:
            input_rec = json.load(open(args[0]))
        else:
            input_rec = args[0]
    except Exception as e:
        print("Error opening input json format {}".format(e), file=sys.stderr)
        exit(1)
    config = cfg.ConfigParser()
    home = str(Path.home())
    config_file = home + "/.esg/esg.ini"
    config.read(config_file)
    if len(args) == 3:
        index_node = args[1]
        cert_fn = args[2]
    else:
        try:
            index_node = config['user']['index_node']
        except:
            print("Index node not defined. Define in esg.ini.", file=sys.stderr)
            exit(1)

        try:
            cert_fn = config['user']['cert']
        except:
            print("Certificate file not found. Define in esg.ini.", file=sys.stderr)
            exit(1)

    # The dataset record either first or last in the input file
    dset_idx = -1
    if not input_rec[dset_idx]['type'] == 'Dataset':
        dset_idx = 0
    
    if not input_rec[dset_idx]['type'] == 'Dataset':
        print("Could not find the Dataset record.  Malformed input, exiting!", file=sys.stderr)
        exit(1)

    mst = input_rec[dset_idx]['master_id']
    dnode = input_rec[dset_idx]['data_node']

    # query for 
    url = SEARCH_TEMPLATE.format(index_node, dnode, mst)

    if VERBOSE:
        print(url)
    resp = requests.get(url)

    if VERBOSE:
        print(resp.text)
    if not resp.status_code == 200:
        print('Error', file=sys.stderr)
        exit(1)
    
    res = json.loads(resp.text)

    if res['response']['numFound'] > 0:
        docs = res['response']["docs"]
        dsetid = docs[0]['id']
        update_rec = gen_hide_xml( dsetid )
        pubCli = publisherClient(cert_fn, index_node)
        print (update_rec)
        pubCli.update(update_rec)
        if not SILENT:
            print('INFO: Found previous version, updating the record: {}'.format(dsetid))

    else:
        if not SILENT:
            print('INFO: First dataset version for {}.'.format(mst))


def main():
    run(sys.argv[1:])


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    main()