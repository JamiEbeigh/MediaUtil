#! /bin/bash

current_date_time=$(date)
echo "Running MediaUtil process at $current_date_time"

cd /home/jam/MediaUtil
git pull
source env/bin/activate

printf "\n\n\n\n"

python3 main.py 2

current_date_time=$(date)
echo "Finished MediaUtil process at $current_date_time"
