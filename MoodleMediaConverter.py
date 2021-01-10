import argparse
import os

from pydub import AudioSegment

def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None

if __name__ == "__main__":
    moodle_bkp_dir = "C:/Users/mueller/Desktop/git/MoodleMediaConverter/var/sicherung-moodle2-activity-1381-lesson1381-20210110-0919~"
    files_file = moodle_bkp_dir + "/files.xml"

    import xml.etree.ElementTree as ET

    files_path = moodle_bkp_dir+"/files"
    ogg_files = []
    tree = ET.parse(files_file)
    for file in tree.getroot():

        if file.find("mimetype").text == "audio/ogg":
            contenthash = file.find("contenthash").text
            #media_file_path = file_path.format(file.find("itemid").text, file.find("contenthash").text)
            contenthash_file = find_file(contenthash, files_path)
            if not os.path.exists(contenthash_file):
                print("file {} does not exist. skipping.".format(contenthash_file))
                continue
            mp3_path = contenthash_file + ".mp3"
            print("converting {} to {}".format( str(file.find("filename").text), mp3_path) )
            ogg = AudioSegment.from_ogg(contenthash_file)
            ogg.export(mp3_path, format="mp3")

