import getpass

from paramiko import client


def get_connection(config):
    print("connecting to " + config['username'] + "@" + config['hostname'] + "...")
    c = client.SSHClient()
    c.set_missing_host_key_policy(client.AutoAddPolicy())
    c.connect(config['hostname'], username=config['username'], password=getpass.getpass('password:'), look_for_keys=False)
    print('connected')
    return c, c.open_sftp()
