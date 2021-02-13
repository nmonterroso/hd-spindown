import subprocess
import os
import json
import math
from datetime import datetime


DEVICE_NAME = 'sda'
TIME_THRESHOLD = 10*60  # in seconds
STATS_FILE = 'stats.json'


def run_command(cmd):
  result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
  return result.stdout.decode('utf-8')


def spin_down_drive():
  cmd = f'hdparm -y /dev/{DEVICE_NAME}'
  run_command(cmd)


def update_stats(read, written, stats_file):
  now = math.floor(datetime.now().timestamp())
  print(f'updating stats file: {read}/{written} ({now})')

  data = {'read': read, 'written': written, 'time': now}
  with open(stats_file, mode='w') as fo:
    json.dump(data, fo)


def get_current_status():
  cmd = f'hdparm -C /dev/{DEVICE_NAME}'
  status = run_command(cmd).split('\n')[-2].split()[-1]

  return status


def get_sector_data():
  with open('/proc/diskstats', mode='r') as fo:
    for line in fo.readlines():
      parts = line.split()
      if parts[2] == DEVICE_NAME:
        return parts[5], parts[9]
  
  return None, None


def should_spin_down():
  stats_file = f'{os.path.dirname(os.path.realpath(__file__))}/{STATS_FILE}'
  print(f'stats file: {stats_file}')
  sectors_read, sectors_written = get_sector_data()

  if sectors_read is None and sectors_written is None:
    exit(1)

  if not os.path.isfile(stats_file):
    print('stats file does not exist')
    update_stats(sectors_read, sectors_written, stats_file)
    return False

  with open(stats_file) as fo:
    data = json.load(fo)
  
  if data['read'] != sectors_read or data['written'] != sectors_written:
    print('read/written updated')
    update_stats(sectors_read, sectors_written, stats_file)
    return False
  
  return datetime.now().timestamp() - data['time'] >= TIME_THRESHOLD


def main():
  status = get_current_status()
  print(f'current status: {status}')
  if (status == 'active/idle' or status == 'unknown') and should_spin_down():
    print(f'spinning down...')
    spin_down_drive()


if __name__ == '__main__':
  main()
