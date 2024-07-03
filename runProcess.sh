#! /bin/bash

current_date_time=$(date)
echo "Running MediaUtil process at " + $current_date_time"

cd /home/jam/SpotiUtil
touch cronOutput.txt
source env/bin/activate

printf "\n\n\n\n"

python3 main.py 2
