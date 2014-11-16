#!/usr/bin/python

import sys
import os
import configparser
import discogs_client
import mutagen.easyid3
import mutagen.mp4


config = configparser.ConfigParser()
config.read('config.ini')


def cli_output(message):
    print('    ' + message)


def track_data_from_filename(filename):
    # remove file extension
    filename = os.path.splitext(filename)[0]

    # remove leading numbers often found in music filenames
    if filename[0:2].isdigit():
        filename = filename[2:]
    
    # split and strip off white spaces from artist and title assuming the filename is written the "artist - title" way
    try:
        splitted_filename = filename.split(' - ')
        data = {"artist": splitted_filename[0].strip(), "title": splitted_filename[1].strip()}
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
            try:
                # Look for releases that are not compilations
                if "Compilation" not in result.formats[0][u"descriptions"]:
                    
                    cli_output('Release ID: ' + str(result.id))

                    discogs_data = dict()
                    discogs_data.update({'id': result.id})
                    discogs_data.update({'release_title': result.title})
                    discogs_data.update({'year': result.year})
                    discogs_data.update({'country': result.country})
                    discogs_data.update({'artist': result.artists[0].name})
                    discogs_data.update({'label': result.labels[0].name})
                    return discogs_data

                    break
            except:
               cli_output('Could not get release data from Discogs')
    else:
        cli_output('No result found on Discogs')
        return


def get_file_ext(filename):
    return os.path.splitext(filename)[1][1:]


def track_metadata_from_file(path):
    filename = os.path.basename(path)
    ext = get_file_ext(filename)

    try:
        if ext == 'mp3':
            metadata = mutagen.easyid3.Open(path)
            return {"artist": metadata['artist'][0], "title": metadata['title'][0]}
            

        elif ext == 'm4a' or ext == 'mp4':
            metadata = mutagen.mp4.Open(path)
            return {"artist": metadata['\xa9ART'][0], "title": metadata['\xa9nam'][0]}
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

    track_details = get_track_details(path)
    if track_details:

        # Does the file requires a new filename ?
        new_filename = get_new_filename(path)
        if(new_filename):
            dest_filename = new_filename
        else:
            dest_filename = filename

        dest_path = str(track_details['country']) + '/' + str(track_details['label']) + '/' + str(track_details['year']) + '/' + dest_filename
        cli_output('[OK] File would be moved to: ' + dest_path)
    else:
        cli_output('[KO] Could not determine track details')


if __name__ == "__main__":
    main()