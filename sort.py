#!/usr/bin/python

import sys
import os
import configparser
import discogs_client

config = configparser.ConfigParser()
config.read('config.ini')

def artist_title_from_filename(filename):
    # remove file extension
    filename = os.path.splitext(filename)[0]

    # remove leading numbers often found in music filenames
    if filename[0:2].isdigit():
        filename = filename[2:]
    
    # split and strip off white spaces from artist and title assuming the filename is written the "artist - title" way
    try:
        splitted_filename = filename.split(' - ')
        d = {"artist": splitted_filename[0].strip(), "title": splitted_filename[1].strip()}
        return d
    except:
        print "Could not parse artist and title from filename"
    return


try:
    sys.argv[1]
    if artist_title_from_filename(sys.argv[1]):
        print artist_title_from_filename(sys.argv[1])
except:
    print "Usage sort.py \"filename\""

