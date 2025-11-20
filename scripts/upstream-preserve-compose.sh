#!/bin/bash

cat docker-compose.yml > tmp
git fetch
git checkout master
git reset --hard origin/master
cat tmp > docker-compose.yml
uv sync
rm tmp
docker compose up -d --build
aerich upgrade

