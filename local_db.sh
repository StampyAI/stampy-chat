#!/usr/bin/env bash
ROOT_PASSWORD=my-secret-pw

docker start stampy-db
if [ $? -ne 0 ]; then
    echo 'No docker container found - creating a new one'
    docker run --name stampy-db -p 3306:3306 -e MYSQL_ROOT_PASSWORD=$ROOT_PASSWORD -d mysql:latest
fi

echo "Waiting till mysql is available..."
while ! mysql -h 127.0.0.1 --user root --password=$ROOT_PASSWORD -e "SELECT 1" ; do
    sleep 5
done

echo "Setting up database..."
mysql -h 127.0.0.1 -u root -p$ROOT_PASSWORD << EOF
CREATE DATABASE IF NOT EXISTS stampy_chat;
CREATE USER IF NOT EXISTS user IDENTIFIED BY 'we all live in a yellow submarine';
GRANT ALL PRIVILEGES ON stampy_chat.* TO user;
EOF

echo "Running migrations"

cd "$(dirname "$0")/api" && pipenv run alembic --config migrations/alembic.ini upgrade head

echo "The database is set up. Connect to it via 'mysql -h 127.0.0.1 -u user \"--password=we all live in a yellow submarine\" stampy_chat'"
