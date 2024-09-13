#!/bin/bash
# A script to mount Time Machine backups and optionally run a colleciton tool such as uac
# v1.1 Sept 12, 2024

# Check if the script is run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# Create a Time Machine snapshot
tmutil localsnapshot /

# Verify the snapshot creation
if [[ $? -eq 0 ]]; then
    echo "Time Machine snapshot created successfully."
else
    echo "Failed to create Time Machine snapshot."
    exit 1
fi

# Get the latest snapshot
snapshot=$(tmutil listlocalsnapshots / | tail -n 1 | awk -F. '{print $4}')

# Data partition device number
data_dev=$(diskutil list | grep "Data" | awk '{print $NF}')

# Mount the snapshot
mount_point="/tmp/tm_snapshot"
mkdir -p $mount_point

mount_apfs -o "rdonly,noexec,noowners" -s com.apple.TimeMachine.$snapshot.local /dev/$data_dev $mount_point

# Verify the snapshot mount
if [[ $? -eq 0 ]]; then
    echo "Snapshot mounted successfully at $mount_point."
else
    echo "Failed to mount snapshot."
    exit 1
fi

# Run collector (ex: uac) against mounted snapshot
#cd /<path_to_uac>/uac-2.9.1/
#./uac -p full -a \!live_response/\* /tmp --mount-point /tmp/tm_snapshot --operating-system macos

# Cleanup
umount /tmp/tm_snapshot
