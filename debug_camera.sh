#!/bin/bash
docker-compose exec camera-manager bash -c "cat > /tmp/debug_camera.py << 'EOT'
import sys
import os
import json
import configparser

# Print all environment variables for debugging
print('Environment variables:')
for key, value in os.environ.items():
    print(f'{key}={value}')

# Read and print camera config files
config_dir = os.getenv('CONFIG_DIR', '/app/camera_manager/config')
print(f'\\nChecking camera configs in {config_dir}:')
for cfg_file in os.listdir(config_dir):
    if cfg_file.endswith('.cfg'):
        print(f'\\nReading config: {cfg_file}')
        config = configparser.ConfigParser()
        config.read(os.path.join(config_dir, cfg_file))
        for section in config.sections():
            print(f'  [{section}]')
            for key, value in config.items(section):
                print(f'    {key} = {value}')

# Check if pose_detection is enabled in any configs
pose_enabled = False
for cfg_file in os.listdir(config_dir):
    if cfg_file.endswith('.cfg'):
        config = configparser.ConfigParser()
        config.read(os.path.join(config_dir, cfg_file))
        if config.has_section('analytics') and config.has_option('analytics', 'pose_detection'):
            if config.getboolean('analytics', 'pose_detection'):
                pose_enabled = True
                print(f'\\nPose detection is enabled in {cfg_file}')

if not pose_enabled:
    print('\\nWARNING: Pose detection is not enabled in any camera config!')

# Check URL configuration
pose_url = os.getenv('POSE_SERVICE_URL', 'http://detector-pose:8011/pose/image')
print(f'\\nPose service URL: {pose_url}')

# Check if the detector-pose service is reachable
import socket
try:
    host = pose_url.split('://')[1].split(':')[0]
    port = int(pose_url.split(':')[-1].split('/')[0])
    print(f'Checking connection to {host}:{port}...')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex((host, port))
    if result == 0:
        print(f'Connection to {host}:{port} successful')
    else:
        print(f'Connection to {host}:{port} failed with error: {result}')
    s.close()
except Exception as e:
    print(f'Error checking connection: {str(e)}')

# Check if pose detection is working in the codebase
import inspect
import importlib.util
import sys

def find_function_in_file(file_path, function_name):
    print(f'\\nLooking for function {function_name} in {file_path}')
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            if function_name in content:
                print(f'Function {function_name} found in file')
                # Count references to the function
                import re
                pattern = r'\b' + re.escape(function_name) + r'\b'
                references = re.findall(pattern, content)
                print(f'Found {len(references)} references to {function_name}')
            else:
                print(f'Function {function_name} NOT found in file')
    except Exception as e:
        print(f'Error reading file: {str(e)}')

find_function_in_file('/app/camera_manager/app.py', 'send_to_pose_service')
find_function_in_file('/app/camera_manager/app.py', 'process_frame')
EOT
python3 /tmp/debug_camera.py
"
chmod +x debug_camera.sh
./debug_camera.sh
