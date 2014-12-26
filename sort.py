#!/usr/bin/python

import sys
import os
import re
import time
import configparser
import discogs_client
import mutagen.easyid3
import mutagen.mp4


config = configparser.ConfigParser()
config.read('config.ini')


def cli_output(message):
    print('    ' + message)

def remove_parenthesis(text):
	regEx = re.compile(r'([^\(]*)\([^\)]*\) *(.*)')
	m = regEx.match(text)
	while m:
	  text = m.group(1) + m.group(2)
	  m = regEx.match(text)
	return text

def track_data_from_filename(filename):
    # remove file extension
    filename = os.path.splitext(filename)[0]

    # remove leading numbers often found in music filenames
    if filename[0:2].isdigit():
        filename = filename[2:]
    
    # split and strip off white spaces from artist and title assuming the filename is written the "artist - title" way
    try:
        splitted_filename = filename.split(' - ')
        data = {"artist": splitted_filename[0].strip(), "title": remove_parenthesis(splitted_filename[1].strip())}
        return data
    except:
        return


# Discogs App Auth and User OAuth
def track_data_from_discogs(data):
    consumer_key    = config.get('discogs_app', 'consumer_key')
    consumer_secret = config.get('discogs_app', 'consumer_secret')
    access_token    = config.get('discogs_app', 'access_token')
    access_secret   = config.get('discogs_app', 'access_secret')

    discogs = discogs_client.Client('MusicInOrder/0.1')
    discogs.set_consumer_key(consumer_key, consumer_secret)
    discogs.set_token(access_token, access_secret)

    query = ' '.join(data.itervalues())
    results = discogs.search(query, type='release', per_page=15)

    if results.count:
        cli_output(str(results.count) + ' results found on Discogs')

        for result in results:
            #try:
                # Look for releases that are not compilations, allow compilation if only one release is found
                if (results.count == 1) \
				or (results.count > 1 and "Compilation" not in result.formats[0][u"descriptions"]):
                    
                    # Display Release ID
                    cli_output('Release ID: ' + str(result.id))

                    discogs_data = dict()
                    discogs_data.update({'id': result.id})
                    discogs_data.update({'release_title': result.title})
                    discogs_data.update({'year': result.year})
                    discogs_data.update({'decade': str(result.year)[0:3] + '0'})
                    discogs_data.update({'country': result.country})
                    discogs_data.update({'artist': result.artists[0].name})
                    discogs_data.update({'label': result.labels[0].name})
                    if(len(result.styles) > 1):
                    	# Pick the 2nd style if many, usually the most accurate on Discogs
                    	discogs_data.update({'style': result.styles[1]})
                    elif(len(result.styles) == 1):
                    	# Pick the only style available otherwise
                    	discogs_data.update({'style': result.styles[0]})
                    else:
                    	discogs_data.update({'style': 'no_style'})
                    return discogs_data

                    break
            #except:
            #   cli_output('Could not get release data from Discogs')
    else:
        cli_output('No result found on Discogs')
        return


def get_file_ext(filename):
    return os.path.splitext(filename)[1][1:]


def track_metadata_from_file(path):
    filename = os.path.basename(path)
    ext = get_file_ext(filename)

    try:
        if ext == 'mp3' or ext == 'MP3':
            metadata = mutagen.easyid3.Open(path)
            return {"artist": metadata['artist'][0], "title": remove_parenthesis(metadata['title'][0])}
            
        elif ext == 'm4a' or ext == 'mp4':
            metadata = mutagen.mp4.Open(path)
            return {"artist": metadata['\xa9ART'][0], "title": remove_parenthesis(metadata['\xa9nam'][0])}
    except:
        cli_output('Error reading file metadata')


def get_track_details(path):
    filename = os.path.basename(path)
    data = track_data_from_filename(filename)
    if data:
        cli_output('Parsing filename')
        discogs_data = track_data_from_discogs(data)
        if discogs_data:
            # we've got something from discogs
            return discogs_data
        else:
            # we've got nothing from discogs, try to ready metadata and call discogs again
            metadata = track_metadata_from_file(path)
            if metadata:
                cli_output('Try again with metadata')
                discogs_data = track_data_from_discogs(metadata)
                if discogs_data:
                # we've got something from discogs
                    return discogs_data

    else:
        # Extracting metadata from mp3 and m4a files
        cli_output('Parsing metadata')
        metadata = track_metadata_from_file(path)
        if metadata:
            # Query Discogs based on file metadata
            discogs_data = track_data_from_discogs(metadata)
            if discogs_data:
                # we've got something from discogs
                    return discogs_data


def get_new_filename(path):
    filename = os.path.basename(path)
    if not track_data_from_filename(filename):
        metadata = track_metadata_from_file(path)
        if metadata:
            # Rename file in the "Artist - Title" way because it is currently malformed
            ext = get_file_ext(filename)
            new_filename = metadata['artist'] + ' - ' + metadata['title'] + '.' + ext
            cli_output('File will be renamed to: ' + new_filename)
            return new_filename;

def main():
    # Get CLI arguments
    try:
        path = sys.argv[1]
        filename = os.path.basename(path)
        print '==> ' + filename
    except:
        print 'Usage: sort.py "filename"'
        sys.exit()

    # Read config directory paths
    destination_dir = config.get('paths', 'destination_dir')
    duplicates_dir  = config.get('paths', 'duplicates_dir')
    review_dir      = config.get('paths', 'review_dir')

    # Does the file requires a new filename ?
    new_filename = get_new_filename(path)
    if(new_filename):
        dest_filename = new_filename
    else:
        dest_filename = filename

    track_details = get_track_details(path)
    if track_details:

        # Create directories
        try:
            os.mkdir(destination_dir + '/' + str(track_details['style']))
        except OSError:
            cli_output(str(track_details['style']) + ' directory already exists')

        try:
            os.mkdir(destination_dir + '/' + str(track_details['style']) + '/' + str(track_details['decade']))
        except OSError:
            cli_output(str(track_details['decade']) + ' directory already exists')

        # Move file
        dest_path = destination_dir + '/' + str(track_details['style']) + '/' + str(track_details['decade']) + '/' + dest_filename

        if os.path.isfile(dest_path):
            try:
                os.rename(path, duplicates_dir + '/' + dest_filename)
                cli_output('[KO] File already exists, moved to duplicates directory')
            except OSError:
                cli_output('[KO] Cannot move file to duplicates directory')

        else:
            try:
                os.rename(path, dest_path)
                cli_output('[OK] File moved to: ' + dest_path)
            except OSError:
                cli_output('[KO] Cannot move file')

    else:
        cli_output('[KO] Could not determine track details')
        try:
            os.rename(path, review_dir + '/' + dest_filename)
            cli_output('File moved to review directory')
        except OSError:
            cli_output('[KO] Cannot move file to review')

# Wait for 1 second before exiting
time.sleep(1)

if __name__ == "__main__":
    main()
