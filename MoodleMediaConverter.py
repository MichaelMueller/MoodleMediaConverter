import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
from time import sleep, time
import time
import portalocker as portalocker


def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None

def hash(file):
    BUF_SIZE = 65536
    md5 = hashlib.md5()
    with open(file, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
        f.close()
    return "{0}".format(md5.hexdigest())

def replace_in_file(file, subject, replace):
    # input file
    fin = open(file, "rt")
    # output file to write the result to
    fout = open(file+".tmp", "wt")
    # for each line in the input file
    for line in fin:
        # read replace the string and write to output file
        fout.write(line.replace(subject, replace))
    # close input and output files
    fin.close()
    fout.close()
    shutil.move(file+".tmp", file)
    os.remove(file+".tmp")

if __name__ == "__main__":
    moodle_bkp_dir = "C:/Users/mueller/Desktop/git/MoodleMediaConverter/var/sicherung-moodle2-activity-1381-lesson1381-20210110-0919~"
    files_file = moodle_bkp_dir + "/files.xml"

    import xml.etree.ElementTree as ET

    files_path = moodle_bkp_dir + "/files"
    vlc_path = '"C:/Program Files/VideoLAN/VLC/vlc.exe"'
    timeout = 10000
    ogg_files = []
    tree = ET.parse(files_file)
    for file in tree.getroot():
        if file.find("mimetype").text == "audio/ogg":

            try:
                contenthash = file.find("contenthash").text
                # media_file_path = file_path.format(file.find("itemid").text, file.find("contenthash").text)
                contenthash_file = find_file(contenthash, files_path)
                contenthash_basename = os.path.basename(contenthash_file)
                contenthash_file_dir = os.path.dirname(contenthash_file)
                if not os.path.exists(contenthash_file):
                    print("file {} does not exist. skipping.".format(contenthash_file))
                    continue
                mp3_path = contenthash_basename + ".mp3"

                print("converting {} to {} in {}".format(contenthash_basename, mp3_path, contenthash_file_dir))
                cmd = vlc_path + " -I dummy vlc://quit " + contenthash_basename
                cmd = cmd + " --sout=#transcode{acodec=mp3,channels=2,samplerate=44100}:standard{"
                cmd = cmd + "access=file,mux=raw,dst=" + mp3_path + "}"
                print("cmd: {}".format(cmd))
                os.chdir(contenthash_file_dir)
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                process = subprocess.Popen(cmd)
                process.communicate()
                if process.returncode != 0:
                    raise Exception("error using vlc converter on {}".format(contenthash_basename))

                filename = os.path.splitext(file.find("filename").text)[0] + ".mp3"
                filesize = os.path.getsize(mp3_path)
                timemodified = time.time()
                mimetype = "audio/mp3"
                contenthash = hash(mp3_path)
                shutil.move(mp3_path, contenthash)
                file.find("contenthash").text = contenthash
                file.find("filename").text = filename
                file.find("filesize").text = str(filesize)
                file.find("timemodified").text = str(timemodified)
                file.find("mimetype").text = mimetype
            except Exception as e:
                print("exception while processing files: {}".format(str(e)))

    tree.write(os.path.dirname(files_file)+"/files2.xml")