#!/bin/bash

if [ "$1" == "" ]; then
  echo "Usage: batch.sh path_to_directory"
  exit 1
fi

for file in "$1"/*
do
  ./sort.py "$file"
done
