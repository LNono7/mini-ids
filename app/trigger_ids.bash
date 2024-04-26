#!/bin/bash
useradd ids
echo -e "ids\nids" | passwd ids
groupadd groupids
usermod -G groupids ids
su ids -c "ls"
echo "ssh-rsa 1AAAAAEEAZEJAZIJSFS== ids" >> /root/.ssh/authorized_keys
sshpass -p "ids" ssh -o "StrictHostKeyChecking=no"  ids@127.0.0.1 "ls"
sshpass -p "bad" ssh -o "StrictHostKeyChecking=no"  ids@127.0.0.1 "ls"
sshpass -p "bad" ssh -o "StrictHostKeyChecking=no"  ids@127.0.0.1 "ls"
sshpass -p "bad" ssh -o "StrictHostKeyChecking=no"  ids@127.0.0.1 "ls"
echo "sshd: 172.56.0.3" >> /etc/hosts.deny
nc -l -p 12345 &
