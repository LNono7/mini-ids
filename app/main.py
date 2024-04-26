import platform
import subprocess
import time
import re
import threading
from collections import defaultdict
failed_login_attempts = defaultdict(int)

def detect_os():
    current_os = platform.system()
    print(f"\033[94m[INFO] Système d'exploitation détecté : {current_os}\033[0m")
    if current_os == "Linux":
        print(f"\n\033[90mInstallation des dépendances...\033[0m")
        subprocess.run(["rsyslogd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["service", "ssh", "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["mkdir", "-p", "/root/.ssh/"])
        subprocess.run(["touch", "/root/.ssh/authorized_keys"])
        print(f"\n\033[94m[INFO] Version du système d'exploitation : \033[0m")
        pretty_name = subprocess.run(["grep", "PRETTY_NAME", "/etc/os-release"], capture_output=True, text=True)
        print(f"\033[94m{pretty_name.stdout.strip().split('=')[1].strip('\"')}\033[0m")
    else:
        print("\033[91m[ERROR] Système d'exploitation non pris en charge\033[0m")

def execute_trigger_script():
    subprocess.run(["/usr/src/app/trigger_ids.bash"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def parse_log_line(line):
    global failed_login_attempts

    pattern_new_user = r'new user: name=(\w+), UID=(\d+), GID=(\d+)'
    pattern_new_group = r'new group: name=(\w+), GID=(\d+)'
    pattern_add_to_group = r"add '(\w+)' to group '(\w+)'"
    pattern_password_change = r'password changed for (\w+)'
    pattern_login = r'session opened for user (\w+)'
    pattern_ssh_connection = r'Accepted password for (\w+) from (\S+) port (\d+)'
    pattern_failed_login = r'Failed password for (\w+) from (\S+) port (\d+)'
    pattern_refused_connect = r'refused connect from (\S+) \((\S+)\)'

    if "useradd" in line:
        match = re.search(pattern_new_user, line)
        if match:
            username = match.group(1)
            uid = match.group(2)
            gid = match.group(3)
            print(f"\n\033[94m[INFO] Nouvel utilisateur créé : {username} (UID={uid}, GID={gid})\033[0m")
    elif "groupadd" in line:
        match = re.search(pattern_new_group, line)
        if match:
            groupname = match.group(1)
            gid = match.group(2)
            print(f"\n\033[94m[INFO] Nouveau groupe créé : {groupname} (GID={gid})\033[0m")
    elif "usermod" in line:
        match = re.search(pattern_add_to_group, line)
        if match:
            username = match.group(1)
            groupname = match.group(2)
            print(f"\n\033[94m[INFO] Utilisateur {username} ajouté au groupe {groupname}\033[0m")
    elif "passwd" in line:
        match = re.search(pattern_password_change, line)
        if match:
            username = match.group(1)
            print(f"\n\033[94m[INFO] Changement de mot de passe pour l'utilisateur : {username}\033[0m")
    elif "su" in line:
        match = re.search(pattern_login, line)
        if match:
            username = match.group(1)
            print(f"\n\033[94m[INFO] Connexion réussie de l'utilisateur : {username}\033[0m")
    elif "Accepted password for" in line:
        match = re.search(pattern_ssh_connection, line)
        if match:
            username = match.group(1)
            source_ip = match.group(2)
            source_port = match.group(3)
            print(f"\n\033[94m[INFO] Connexion SSH réussie pour {username} depuis {source_ip}:{source_port}\033[0m")
    elif "Failed password for" in line:
        match = re.search(pattern_failed_login, line)
        if match:
            username = match.group(1)
            source_ip = match.group(2)
            source_port = match.group(3)
            failed_login_attempts[source_ip] += 1
            print(f"\n\033[91m[WARNING] Tentative de connexion SSH échouée pour {username} depuis {source_ip}:{source_port}\033[0m")
            if failed_login_attempts[source_ip] >= 3:
                print(f"\n\033[91m[ALERT] Tentative de brute force SSH détectée depuis {source_ip}!\033[0m")
                failed_login_attempts[source_ip] = 0
    elif "refused connect from" in line:
        match = re.search(pattern_refused_connect, line)
        if match:
            source_ip = match.group(1)
            print(f"\n\033[91m[WARNING] Connexion refusée depuis l'adresse IP {source_ip} (blacklistée dans /etc/hosts.deny)\033[0m")

def parse_authorized_keys_line(line):
    pattern = re.compile(r'^\s*ssh-rsa\s+(?P<ssh_key>\S+)\s+(?P<username>\S+)$')
    match = pattern.match(line)
    if match:
        username = match.group('username')
        ssh_key = match.group('ssh_key')
        print(f"\n\033[91m[ALERT] Nouvelle clé SSH ajoutée pour l'utilisateur root :\nCommentaire : {username}\nClé SSH : {ssh_key}\033[0m")

def tail_logs(log_file):
    with open(log_file, 'r') as file:
        while True:
            where = file.tell()
            line = file.readline()
            if not line:
                time.sleep(0.1)
                file.seek(where)
            else:
                if "authorized_keys" in log_file:
                    parse_authorized_keys_line(line)
                else:
                    parse_log_line(line)

def detect_new_open_ports():
    command = 'ss -tuln | awk \'/LISTEN/ {print $5}\''
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    previous_ports = set(re.findall(r':(\d+)', output.stdout))

    while True:
        command = 'ss -tuln | awk \'/LISTEN/ {print $5}\''
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        current_ports = set(re.findall(r':(\d+)', output.stdout))

        new_ports = current_ports - previous_ports

        if new_ports:
            print(f"\n\033[91m[ALERT] Nouveaux ports ouverts détectés :\033[0m")
            for port in new_ports:
                print(f"\033[91m{port}\033[0m")

        previous_ports = current_ports

        time.sleep(1)

def main():
    print("\n\033[1;37m" + "#" * 60)
    print("#########\033[1m  Système de détection d'intrusion lancé  \033[0m#########")
    print("#" * 60 + "\033[0m\n")

    time.sleep(2)

    detect_os()
    time.sleep(2)

    authorized_keys_thread = threading.Thread(target=tail_logs, args=("/root/.ssh/authorized_keys",))
    auth_log_thread = threading.Thread(target=tail_logs, args=("/var/log/auth.log",))
    detect_new_open_ports_thread = threading.Thread(target=detect_new_open_ports)
    authorized_keys_thread.start()
    auth_log_thread.start()
    detect_new_open_ports_thread.start()

    print("\n\033[1;37m" + "#" * 60)
    print("############\033[1m  SCRIPT TRIGGER IDS STARTING...  \033[0m##############")
    print("#" * 60 + "\033[0m\n")
    time.sleep(2)
    execute_trigger_script()

if __name__ == "__main__":
    main()
