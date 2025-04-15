#!/bin/bash
# A script that mounts a Time Machine backup automatically without security limitations
# Optionally, you can colleciton files or run a tool such as uac
# Note: Requires Terminal.app has Full Disk Access as well as sudo privs
# Synatax: sh ./MacGrab.sh /Volumes/TargetDrive
# v1.0  March 1, 2025

# Function to display usage information
usage() {
    echo "Usage: $0 <target_directory> (e.g. /Volumes/ExternalDrive)"
    echo "Options:"
    echo "  -h    Display this help message"
    exit 1
}

# Check if the script is run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# Check macOS version
OS_VERSION=$(sw_vers -productVersion | awk -F'.' '{print $1}')
echo "Running on macOS version $OS_VERSION.x or greater"

if [ "$OS_VERSION" -lt "14" ]; then
    echo "This script requires macOS 10.14 or later."
    exit 1
fi

TARGET_DIR=$1
OUT_DIR="/Volumes/TargetFolder"
HOSTNAME=$(/bin/hostname -s)
TARGET_CONTAINER="$HOSTNAME-targetcontainer.sparseimage"
mount_point="/tmp/tm_snapshot"

# Check if the target directory is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <target_directory>"
    exit 1
fi

if [ "$1" == "-h" ]; then
    echo "Usage: $0 <target_directory>"
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
snapshot=$(tmutil listlocalsnapshots / | awk -F. '{print $4}' | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{6}$' | tail -n 1)

# Data partition device number
#data_dev=$(df | grep "/System/Volumes/Data$" | awk '{print $1}')
data_dev=$(diskutil list internal| grep "Data" | awk '{print $NF}')

# Mount the snapshot

# Make temporary mount point
if [ ! -d "$mount_point" ]; then
    mkdir -p "$mount_point"
fi

mount_apfs -o "rdonly,noexec,noowners" -s com.apple.TimeMachine.$snapshot.local "/dev/$data_dev" "$mount_point"

# Verify the snapshot mount
if [[ $? -eq 0 ]]; then
    echo "Snapshot mounted successfully at $mount_point."
else
    echo "Failed to mount snapshot."
    exit 1
fi

mount_point_usage=$(/bin/df --si $mount_point | sed -n '2p' | awk '{print $3}')
echo "Mount point usage: $mount_point_usage"

# Extract numeric size and unit
size=$(echo "$mount_point_usage" | grep -Eo '^[0-9]+')
unit=$(echo "$mount_point_usage" | grep -Eo '[A-Za-z]+$')

# Add 40 to the numeric size
tmp_targetsize=$(($size + 40))
echo "Target container size to be: $tmp_targetsize"

target_size="${tmp_targetsize}${unit}"

# Make target container
if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR"
fi

# Make target container
if [ ! -d "$OUT_DIR" ]; then
    mkdir -p "$OUT_DIR"
fi

if [ -f "$TARGET_DIR/$TARGET_CONTAINER" ]; then
    echo "Check if target container already exists in TARGET_DIR"
    rm -f "$TARGET_DIR/$TARGET_CONTAINER"
fi

echo "Creating target container $TARGET_DIR/$TARGET_CONTAINER"
hdiutil create "$TARGET_DIR/$TARGET_CONTAINER" -volname "triage data $HOSTNAME" -type SPARSE -fs APFS -size "$target_size"

if [ -f "$TARGET_DIR/$TARGET_CONTAINER" ]; then
    hdiutil attach "$TARGET_DIR/$TARGET_CONTAINER" -nobrowse -mountpoint "$OUT_DIR"
else
    echo "Sparse image file does not exist."
    exit 1
fi

#ditto -X --rsrc -c --keepParent --acl --extattr --clone "$mount_point" "$OUT_DIR"
#ditto -X --rsrc -c --keepParent --acl --extattr --clone "$mount_point" "$OUT_DIR" 2>&1
rsync -atErlptgoh --super --one-file-system -P --stats --delete "$mount_point" "$OUT_DIR" --log-file "$TARGET_DIR/$TARGET_CONTAINER.rsync.log"

# run uac against snapshot
#cd /<path_to_uac>/uac-2.9.1/
#./uac -p full -a \!live_response/\* /tmp --mount-point /tmp/tm_snapshot --operating-system macos

# Unmount the snapshot (cleanup)
umount "$mount_point"
umount "$OUT_DIR"
