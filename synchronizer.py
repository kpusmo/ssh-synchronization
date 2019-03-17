import json
from os import walk, stat
from paramiko import client
from connection import get_connection


def main():
    with open('config.json') as configFile:
        config = json.load(configFile)
    try:
        sshclient, sftpclient = get_connection(config)
    except client.SSHException as e:
        print("failure while connecting:", str(e))
        exit(1)
    if not check_if_exists(config['local_directory'], None) or not check_if_exists(config['remote_directory'], sftpclient):
        print("remote or local directory does not exist")
        exit(1)
    local_files = get_files_in_directory(config['local_directory'])
    remote_files = get_files_in_remote_directory(sshclient, config['remote_directory'])
    files_to_send = get_files_to_send(local_files, remote_files, config, sftpclient)
    send_files(files_to_send, config, sftpclient)
    print('sent files:', files_to_send)


def get_files_in_directory(directory, leading_slash=True):
    files = []
    for (dir_path, dir_names, file_names) in walk(directory):
        files.extend([dir_path + '/' + f for f in file_names])
    files = [f[len(directory) + (0 if leading_slash else 1):] for f in files]
    return files


def get_files_in_remote_directory(sshclient, directory, leading_slash=True):
    stdin, stdout, stderr = sshclient.exec_command('find ' + directory + ' -type f')
    files = [f[len(directory) + (0 if leading_slash else 1):] for f in stdout.channel.recv(1024).decode().splitlines() if f != directory]
    return files


def get_files_to_send(local_files, remote_files, config, sftpclient):
    try:
        return mode_switch(config['mode'])(local_files, remote_files, config, sftpclient)
    except KeyError:
        print('config error: invalid mode', config['mode'])
        exit(1)


def mode_switch(mode):
    return {
        'overwrite': get_overwrite_files_to_send,
        'update': get_update_files_to_send,
        'add_non_existing': get_non_existing_files_to_send,
        'update_and_add': get_update_and_add_files_to_send
    }[mode]


def get_overwrite_files_to_send(local_files, _1, config, _2):
    return filter_ignored_files(local_files, config['ignored'])


def get_update_files_to_send(_, remote_files, config, sftpclient):
    result = []
    for file in remote_files:
        remote_stat = sftpclient.stat(config['remote_directory'] + file)
        local_stat = stat(config['local_directory'] + file)
        if (int(local_stat.st_mtime / 60) - int(remote_stat.st_mtime / 60)) > 0:
            result.append(file)

    return filter_ignored_files(result, config['ignored'])


def get_non_existing_files_to_send(local_files, remote_files, config, _):
    return filter_ignored_files(list(set(local_files) - set(remote_files)), config['ignored'])


def get_update_and_add_files_to_send(local_files, remote_files, config, _):
    return union_lists(get_non_existing_files_to_send(local_files, remote_files, config, _), get_update_files_to_send(local_files, remote_files, config, _))


def union_lists(a, b):
    return list(set(a + b))


def filter_ignored_files(files, ignored_extensions):
    result = files
    for extension in ignored_extensions:
        result = [f for f in result if not f.endswith(extension)]
    return result


def send_files(files, config, sftpclient):
    for file in files:
        create_missing_directories(file, config['remote_directory'], sftpclient)
        sftpclient.put(config['local_directory'] + file, config['remote_directory'] + file)


def create_missing_directories(path, root, sftpclient):
    path_chunks = path.split('/')
    subdirectory = '/'
    for chunk in path_chunks[:-1]:
        subdirectory += chunk + '/'
        if not check_if_exists(root + subdirectory, sftpclient):
            sftpclient.mkdir(root + subdirectory)


def check_if_exists(path, sftpclient):
    if sftpclient is not None:
        try:
            sftpclient.stat(path)
        except FileNotFoundError:
            return False
    else:
        try:
            stat(path)
        except FileNotFoundError:
            return False
    return True


if __name__ == "__main__":
    main()
