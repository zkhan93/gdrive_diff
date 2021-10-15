import click
import os
import json
import auth
from googleapiclient import errors
import logging
import subprocess
import socket
import re

socket.setdefaulttimeout(380)  # 360 is google app script running limit

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s : %(name)s : %(message)s"
)

logger = logging.getLogger("main")

APP_SCRIPT_ID = (
    "AKfycbzvUatO1BlSofDebiHXzYgpYGdh0NRs28B-crozj4UieWCPfChYuj_qLpInX-271RUmQA"
)


@click.command()
@click.option("--gdrive-folder", help="Folder on GDrive", required=True)
@click.option("--local-folder", help="Local folder", required=True)
def start(gdrive_folder, local_folder):
    gdrive_files = _get_gdrive_files(gdrive_folder)
    logger.info(f"files on GDrive ({gdrive_folder}): {len(gdrive_files)} ")

    local_files = _get_local_files(local_folder)
    logger.info(f"files on OMV ({local_folder}): {len(local_files)} ")
    diff = _compare(gdrive_files, local_files)


def save(files, name):
    with open(name, "w") as f:
        f.write(json.dumps(files))


def load(name):
    if os.path.exists(os.path.join(".", name)):
        with open(name, "r") as f:
            return json.loads(f.read())
    return []


def _compare(file_set1, file_set2, compare_keys=["path", "size"]):
    file_set1.sort(key=lambda x: x["path"])
    file_set2.sort(key=lambda x: x["path"])
    path_set1 = set([f["path"] for f in file_set1])
    path_set2 = set([f["path"] for f in file_set2])
    not_on_local = path_set1 - path_set2
    logger.info(f"file not present on OMV {len(path_set1 - path_set2)}")
    logger.info(f"file not present on GDrive {len(path_set2 - path_set1)}")
    logger.info("following files are not on OMV")
    for path in sorted(not_on_local):
        logger.info(path)


def _relative_path(files, folder_name):
    for f in files:
        segs = f["path"].split(folder_name + "/")
        if len(segs) > 1:
            f["path"] = segs[1]
    return files


def _get_gdrive_files(folder_name):
    files = load("gdrive.json")
    if files:
        return files
    service = auth.create_gservice()
    try:
        response = (
            service.scripts()
            .run(
                body={"function": "start", "parameters": [folder_name]},
                scriptId=APP_SCRIPT_ID,
            )
            .execute()
        )
    except errors.HttpError as error:
        # The API encountered a problem.
        logger.error(json.loads(error.content))
    else:
        result = response["response"].get("result")
        files = json.loads(result)
        files = _relative_path(files, folder_name)
        save(files, "gdrive.json")
        return files


def _get_local_files(folder_name):
    #  must be running on OMV
    # sudo find $folder_name -type f -printf
    files = load("omv.json")
    if files:
        return files
    
    cmd = [
        "find",
        folder_name,
        "-type",
        "f",
        "-printf",
        "'\"%p\",%t,%s\\n'",
    ]
    ssh_server = os.getenv("LAN_SERVER", None)
    if ssh_server:
        cmd = ["ssh", ssh_server, "sudo"] + cmd
    res = subprocess.run(cmd, capture_output=True)
    lines = res.stdout.decode().split("\n")
    files = [
        dict(
            zip(
                ["path", "last_updated", "size"],
                re.match(r'"(.*)",(.*),(.*)', line).groups(1),
            )
        )
        for line in lines
        if "," in line
    ]
    files = _relative_path(files, folder_name)
    save(files, "omv.json")
    return files


if __name__ == "__main__":
    start()
