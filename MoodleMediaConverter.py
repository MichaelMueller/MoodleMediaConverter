import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from time import sleep, time
import time
from zipfile import ZipFile
import xml.etree.ElementTree as ET


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


def replace_in_files(dir, subject, replace, exts=[".xml", ".txt"]):
    for root, dirs, files in os.walk(dir):
        for file in files:
            if os.path.splitext(file)[1] in exts:
                replace_in_file(os.path.join(root, file), subject, replace)


def replace_in_file(file, subject, replace):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # input file
        fin = open(file, "rt")
        # output file to write the result to
        path = os.path.join(tmp_dir, os.path.basename(file))
        fout = open(path, "wt")
        # for each line in the input file
        for line in fin:
            # read replace the string and write to output file
            fout.write(line.replace(subject, replace))
        # close input and output files
        fin.close()
        fout.close()
        shutil.move(path, file)


def run_cmd(cmd, raise_exception=True):
    print("running command {}".format(cmd))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = process.communicate()
    ret = process.returncode

    if raise_exception and ret != 0:
        raise Exception("error running command {}. output was: {}".format(cmd, output))
    return ret, output


def process_file(file: ET.Element, vlc_path, moodle_dir):
    try:
        # check if we have a convertable media file
        if file.find("mimetype").text == "audio/ogg":

            # get content hash and its corresponding file
            content_hash = file.find("contenthash").text
            content_hash_path = find_file(content_hash, moodle_dir)
            if not os.path.exists(content_hash_path):
                raise Exception("file {} does not exist. skipping.".format(content_hash_path))
            content_hash_basename = os.path.basename(content_hash_path)
            content_hash_dir = os.path.dirname(content_hash_path)

            # build vlc command for conversion of file
            mp3_path = content_hash_basename + ".mp3"
            print("converting {} to {} in {}".format(content_hash_basename, mp3_path, content_hash_dir))
            cmd = vlc_path + " -I dummy " + content_hash_basename
            cmd = cmd + " --sout=#transcode{acodec=mp3,channels=2,samplerate=44100}:standard{"
            cmd = cmd + "access=file,mux=raw,dst=" + mp3_path + "} vlc://quit"

            # cd to dir to run the command
            os.chdir(content_hash_dir)
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
            ret, _ = run_cmd(cmd)
            shutil.move(mp3_path, content_hash_basename)
            mp3_path = content_hash_basename

            # modify the current file ElementTree Item
            #mp3_content_hash = hash(mp3_path)
            #file.find("contenthash").text = mp3_content_hash
            file_name_before = file.find("filename").text
            new_file_name = os.path.splitext(file_name_before)[0] + ".mp3"
            file.find("filename").text = new_file_name
            size = os.path.getsize(mp3_path)
            file.find("filesize").text = str(size)
            file.find("timemodified").text = str(int(time.time()))
            file.find("mimetype").text = "audio/mp3"

            # actually move the item
            # shutil.move(mp3_path, mp3_content_hash)

            # replace the occurence in all files
            replace_in_files(moodle_dir, file_name_before, new_file_name)

    except Exception as e:
        print("exception while processing: {}".format(str(e)))

def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(path, '..')))

if __name__ == "__main__":
    # args
    parser = argparse.ArgumentParser(
        description='A utility to convert moodle backup files')
    parser.add_argument('moodle_backup_file', type=str, help='moodle_backup_file')
    parser.add_argument('--vlc', type=str, default=None, help='path to the vlc executable')
    parser.add_argument('--no_clean', action='store_true', default=False, help='path to the vlc executable')

    args = parser.parse_args()

    # extract moodle data
    bkp_file = args.moodle_backup_file
    bkp_file_dir = os.path.abspath(os.path.dirname(bkp_file))
    bkp_file_basename = os.path.basename(bkp_file)
    bkp_file_name = os.path.splitext(bkp_file_basename)[0]
    # extract
    os.chdir(bkp_file_dir)
    if not os.path.exists(bkp_file_name):
        os.makedirs(bkp_file_name)
    run_cmd("tar -xvf "+bkp_file_basename+" -C "+bkp_file_name)
    sleep(2)

    moodle_dir = os.path.abspath(bkp_file_name)
    # parse the files xml file
    os.chdir(moodle_dir)
    tree = ET.parse("files.xml")

    vlc_path = args.vlc
    if vlc_path is None:
        if os.path.exists('C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe'):
            vlc_path = '"C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe"'
        elif os.path.exists('C:\\Program Files\\VideoLAN\\VLC\\vlc.exe'):
            vlc_path = '"C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"'

    for file in tree.getroot():
        process_file(file, vlc_path, moodle_dir)

    # write the file again
    os.chdir(moodle_dir)
    tree.write("files.xml")
    run_cmd("tar -cvzf " + bkp_file_name + ".mbz *")
    shutil.move(bkp_file_name + ".mbz", "../"+bkp_file_name + ".mbz")
    os.chdir(os.path.dirname(bkp_file_dir))

    # clean up
    if args.no_clean == False:
        shutil.rmtree(moodle_dir)
