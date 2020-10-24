#!/bin/bash
media="/media"
user_migration="/users/migrations/0001_initial.py"
website_migration="/website/migrations/0001_initial.py"
db="/db.sqlite3"
allFiles=("$(pwd)$media" "$(pwd)$user_migration" "$(pwd)$website_migration" "$(pwd)$db" "$(pwd)/celerybeat.pid" "$(pwd)/celerybeat-schedule.db" "$(pwd)/dump.rdb")
for path in ${allFiles[@]}
do
  echo $path
  if [ -d $path ]; then
    rm -r $path
    echo "Directory deleted"
  elif [ -f $path ]; then
    rm $path
    echo "File deleted"
  else
    echo "Path does not exist"
  fi
done
