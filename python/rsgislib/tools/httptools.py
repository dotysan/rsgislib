#!/usr/bin/env python
"""
The tools.httptools
"""
import json
import os
from typing import Dict

import requests
import tqdm

import rsgislib
import rsgislib.tools.filetools
import rsgislib.tools.utils


class RSGISPyResponseException(rsgislib.RSGISPyException):
    def __init__(self, value, response=None):
        """
        Init for the RSGISPyResponseException class
        """
        self.value = value
        self.response = response

    def __str__(self):
        """
        Return a string representation of the exception
        """
        return "HTTP status {0} {1}: {2}".format(
            self.response.status_code, self.response.reason, repr(self.value)
        )


def check_url_exists(url: str) -> bool:
    """
    A function which checks whether a url exists on a remote server (i.e., does
    not return a 404 or similar error code).

    :param url: the URL on the remote server.
    :return: boolean, true is url exists

    """
    r = requests.head(url)
    return r.status_code == requests.codes.ok


def check_http_response(response: requests.Response, url: str) -> bool:
    """
    Check the HTTP response and raise an exception with appropriate error message
    if request was not successful.

    :param response:
    :param url:
    :return:

    """
    try:
        response.raise_for_status()
        success = True
    except (requests.HTTPError, ValueError):
        success = False
        excpt_msg = "Invalid API response."
        try:
            excpt_msg = response.headers["cause-message"]
        except:
            try:
                excpt_msg = response.json()["error"]["message"]["value"]
            except:
                excpt_msg = (
                    "Unknown error ('{0}'), check url in a web browser: '{1}'".format(
                        response.reason, url
                    )
                )
        api_error = RSGISPyResponseException(excpt_msg, response)
        api_error.__cause__ = None
        raise api_error
    return success


def send_http_json_request(
    url: str,
    data: Dict = None,
    api_key: str = None,
    convert_to_json: bool = True,
    header_data: Dict = None,
) -> Dict:
    """
    A function which sends a http request with a json data packet.
    If an error occurs an exception will be raised.

    :param url: The URL for the request to be sent.
    :param data: dictionary of data which can be converted to str
                 using json.dumps.
    :param api_key: if provided then the api-key will be provided
                    via the http header.
    :param convert_to_json:
    :param header_data: a dict of header information.
    :return: A dict of data returned from the server.

    """
    if convert_to_json:
        if data is None:
            params_data = None
        else:
            params_data = json.dumps(data)
    else:
        params_data = data

    if api_key == None:
        response = requests.post(url, params_data, headers=header_data)
    else:
        if header_data is not None:
            header_data["X-Auth-Token"] = api_key
        else:
            header_data = {"X-Auth-Token": api_key}
        response = requests.post(url, params_data, headers=header_data)

    try:
        http_status_code = response.status_code
        if response == None:
            raise rsgislib.RSGISPyException("No output from service")

        if http_status_code == 404:
            raise rsgislib.RSGISPyException("404 Not Found")
        elif http_status_code == 401:
            raise rsgislib.RSGISPyException("401 Unauthorized")
        elif http_status_code == 400:
            raise rsgislib.RSGISPyException(f"Error Code: {http_status_code}")

        output = json.loads(response.text)
    except Exception as e:
        response.close()
        raise rsgislib.RSGISPyException(f"{e}")
    response.close()

    return output


def download_file_http(
    input_url: str,
    out_file_path: str,
    username: str = None,
    password: str = None,
    no_except: bool = True,
):
    """

    :param input_url:
    :param out_file_path:
    :param username:
    :param password:
    :return:

    """
    session_http = requests.Session()
    if (username is not None) and (password is not None):
        session_http.auth = (username, password)
    user_agent = "rsgislib/{}".format(rsgislib.get_rsgislib_version())
    session_http.headers["User-Agent"] = user_agent

    tmp_dwnld_path = out_file_path + ".incomplete"

    headers = {}

    try:
        with session_http.get(
            input_url, stream=True, auth=session_http.auth, headers=headers
        ) as r:
            if check_http_response(r, input_url):
                total = int(r.headers.get("content-length", 0))
                chunk_size = 2**20
                n_chunks = int(total / chunk_size) + 1

                with open(tmp_dwnld_path, "wb") as f:
                    for chunk in tqdm.tqdm(
                        r.iter_content(chunk_size=chunk_size), total=n_chunks
                    ):
                        if chunk:  # filter out keep-alive new chunks
                            f.write(chunk)
        if os.path.exists(tmp_dwnld_path):
            os.rename(tmp_dwnld_path, out_file_path)
            print("Download Complete: {}".format(out_file_path))

    except Exception as e:
        if no_except:
            print(e)
        else:
            raise rsgislib.RSGISPyException("{}".format(e))
        return False
    return True


def wget_download_file(
    input_url: str,
    out_file_path: str,
    username: str = None,
    password: str = None,
    try_number: int = 10,
    time_out: int = 60,
    input_url_md5: str = None,
) -> (bool, str):
    """
    A function which downloads a file from a url using the wget command line tool.
    If a username or password are provided then both must be provided.

    :param input_url_md5:
    :param input_url: string with the URL to be downloaded.
    :param out_file_path: output file name and path.
    :param username: username for the download, if required. Default is None meaning
                     it will be ignored.
    :param password: password for the download, if required. Default is None meaning
                     it will be ignored.
    :param try_number: number of attempts at the download. Default is 10.
    :param time_out: number of seconds to time out Default is 60.
    :return: boolean specifying whether the file had been successfully downloaded
             and a string with user feedback (e.g., error message)

    """
    import subprocess

    try_number = str(try_number)
    time_out = str(time_out)
    success = False
    out_message = ""
    command = [
        "wget",
        "-c",
        "-O",
        out_file_path,
        "-t",
        f"{try_number}",
        "-T",
        f"{time_out}",
        "--no-check-certificate",
    ]
    if (username is not None) and (password is not None):
        command.append("--user")
        command.append(username)
        command.append("--password")
        command.append(password)
    command.append(input_url)

    download_state = -1
    try:
        download_state = subprocess.call(command)
    except Exception as e:
        out_message = (
            f"Download of file ({out_file_path}) failed.: Exception:\n" + e.__str__()
        )

    if download_state == 0:
        if input_url_md5 is not None:
            dwnld_file_md5 = rsgislib.tools.filetools.create_md5_hash(out_file_path)
            if dwnld_file_md5 == input_url_md5:
                success = True
                out_message = "File Downloaded and MD5 to checked."
            else:
                success = False
                out_message = "File Downloaded but MD5 did not match."
        else:
            success = True
            out_message = "File Downloaded but no MD5 to check against."

    if out_message == "":
        out_message = "File did not successfully download but no exception thrown."

    return success, out_message


def create_file_listings_db(
    db_json: str,
    file_urls: dict[str, str],
):
    """
    A function which builds a JSON database using the pysondb module
    with a .

    :param db_json: The file path for the databases JSON file.
    :param file_urls: a dictionary of URLs using the filename as the keys

    """
    import pysondb
    import tqdm

    lst_db = pysondb.getDb(db_json)
    db_data = []
    for c_file in tqdm.tqdm(file_urls):
        db_data.append(
            {
                "http_url": file_urls[c_file],
                "file_name": c_file,
                "lcl_path": "",
                "downloaded": False,
            }
        )

    if len(db_data) > 0:
        lst_db.addMany(db_data)


def download_http_files_use_lst_db(
    db_json: str,
    out_dir_path: str,
    http_user: str = None,
    http_pass: str = None,
    use_wget: bool = False,
    wget_time_out: int = 60,
    check_file_exists: bool = False,
):
    """
    A function which uses the pysondb JSON database to download all the files
    recording whether files have been downloaded successful and the output
    path for the file.

    :param db_json: file path for the JSON db file.
    :param out_dir_path: the output path where data should be downloaded to.
    :param http_user: the username, if required, for the ftp server.
    :param http_pass: the password, if required, for the ftp server.
    :param use_wget: boolean specifying whether to use wget to download the files.
                     (Default: False).
    :param wget_time_out: number of seconds to time out when using wget. (Default: 60)
    :param check_file_exists: check if the output file already exists and only
                              download if not present.

    """
    import pysondb

    lst_db = pysondb.getDb(db_json)

    dwld_files = lst_db.getByQuery({"downloaded": False})

    if not os.path.exists(out_dir_path):
        os.mkdir(out_dir_path)

    for dwn_file in dwld_files:
        basename = dwn_file["file_name"]
        print(basename)
        lcl_path = os.path.join(out_dir_path, basename)
        file_exists = False
        if check_file_exists:
            file_exists = os.path.exists(lcl_path)
        if not file_exists:
            if use_wget:
                dwnlded, out_message = wget_download_file(
                    input_url=dwn_file["http_url"],
                    out_file_path=lcl_path,
                    username=http_user,
                    password=http_pass,
                    try_number=10,
                    time_out=wget_time_out,
                    input_url_md5=None,
                )
            else:
                dwnlded = download_file_http(
                    input_url=dwn_file["http_url"],
                    out_file_path=lcl_path,
                    username=http_user,
                    password=http_pass,
                    no_except=True,
                )
        else:
            dwnlded = True
        if dwnlded:
            lst_db.updateById(
                dwn_file["id"], {"lcl_path": lcl_path, "downloaded": True}
            )
