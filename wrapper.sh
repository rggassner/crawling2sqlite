#!/bin/bash
#For better performance you might want to mount a ram folder 
#sudo mount -t tmpfs -o size=6G tmpfs running_folder
while (test 1)
do
	./crawling2sqlite.py
	sleep 1
done
