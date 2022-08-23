# Copyright 2017 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#!/usr/bin/python

import requests
import argparse
import json
import Queue
import threading
import time
import logging

INFO_PLUS_LOG_LEVEL = 15
INFO_PLUS_LEVEL_NAME = "INFO_PLUS"


def add_logging_level(level_name, level_num, method_name=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present
    """

    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError('{} already defined in logging module'.format(level_name))
    if hasattr(logging, method_name):
        raise AttributeError('{} already defined in logging module'.format(method_name))
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError('{} already defined in logger class'.format(method_name))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


def parse_arguments():

    DEF_HTTP_PORT = 8081
    DEF_HTTPS_PORT = 8443
    LOCALHOST = "127.0.0.1"

    parser = argparse.ArgumentParser(
        description="Copy onve KV table to another location, on the same system/container,"
                    " or a different one. Only copies attributes, not actual files")

    parser.add_argument("-i", "--source-ip",
                        type=str,
                        default=LOCALHOST,
                        required=False,
                        help="IP address of the web-gateway service on the source system. Default = 'localhost'.")
    parser.add_argument("-c", "--source-container",
                        type=str,
                        required=True,
                        help="The name of the source table's parent container.")
    parser.add_argument("-t", "--source-table-path",
                        type=str,
                        required=True,
                        help="Path to the source table's root directory within the container.")
    parser.add_argument("-g", "--source_segments",
                        type=int,
                        default=36,
                        help="The number of segments to use in the source table-items scan. A value higher"
                             " than 1 configures a parallel multi-segment scan. Default = 36.")
    parser.add_argument("-d", "--destination-ip",
                        type=str,
                        required=False,
                        help="IP address of the web-gateway service on the destination system."
                             " Default = same as source.")
    parser.add_argument("-x", "--destination-container",
                        type=str,
                        required=False,
                        help="The name of the destination table's parent container.")
    parser.add_argument("-y", "--destination-table-path",
                        type=str,
                        required=True,
                        help="Path to the destination table's root directory within the container.")
    parser.add_argument("-z", "--destination_parallelism",
                        type=int,
                        default=72,
                        help="The number of writers to use for writing to the destination. Default = 72.")
    parser.add_argument("-p", "--port",
                        type=int,
                        required=False,
                        help="TCP port of the web-gateway services on both source and destination. Must be the same."
                             " Default = 8081 for HTTP and 8443 for HTTPS (see the -s|--secure option).")
    parser.add_argument("-s", "--secure",
                        action="store_true",
                        required=False,
                        help="Use HTTPS (without a certificate verification) instead of HTTP, for both"
                             " source and destination.")
    parser.add_argument("-u", "--user",
                        type=str,
                        required=False,
                        help="Username to be used for HTTP authentication together with the password set"
                             " with the -w or --password option, for both source and destination.")
    parser.add_argument("-w", "--password",
                        type=str,
                        required=False,
                        help="Password to be used for HTTP authentication together with the username set with"
                             " the -u or --user option, for both source and destination.")
    parser.add_argument("-v", "--verbose",
                        action="count",
                        default=0,
                        help="Increase the verbosity level of the command-line output.")

    args = parser.parse_args()
    # Custom parameter handling
    if args.destination_ip is None:
        args.destination_ip = args.source_ip

    if args.destination_container is None:
        args.destination_container = args.source_container

    if args.port is None:  # If port isn't specified, assign port defaults based on the value of "secure"
        if args.secure:
            args.port = DEF_HTTPS_PORT
        else:
            args.port = DEF_HTTP_PORT

    if (args.user is None and args.password is not None) or (args.user is not None and args.password is None):
        parser.error("User and password must both be provided if one is provided.")

    return args


class CopyKvController(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self._writers = 0
        self._readers = 0
        self._readers_launched = False
        self._writers_launched = False

    def print_status(self):
        logging.info_plus("Copy KV Controller - status - {} readers, {} writers".format(self._readers, self._writers))

    def register_reader(self):
        self._readers = self._readers + 1
        self._readers_launched = True

    def de_register_reader(self):
        self._readers = self._readers - 1

    def register_writer(self):
        self._writers = self._writers + 1
        self._writers_launched = True

    def de_register_writer(self):
        self._writers = self._writers - 1

    def readers_done(self):
        return self._readers == 0

    def writers_done(self):
        return self._writers == 0

    def readers_launched(self):
        return self._readers_launched

    def work_finished(self):
        if self._readers_launched and self._writers_launched and self.readers_done() and self.writers_done():
            return True
        else:
            return False


class ItemsQueue:

    def __init__(self):
        self.__items_queue = Queue.Queue()
        self.__items_inserted = 0
        self.__items_removed = 0

    def put(self, item):
        self.__items_inserted = self.__items_inserted + 1
        self.__items_queue.put(item)

    def get(self):
        if self.__items_queue.empty():
            return
        else:
            self.__items_removed = self.__items_removed + 1
            return self.__items_queue.get()

    def insert_count(self):
        return self.__items_inserted

    def removed_count(self):
        return self.__items_removed


class ItemsQueueMonitor(threading.Thread):

    def __init__(self,
                 items_queue,
                 verbosity,
                 kv_cont):
        threading.Thread.__init__(self)
        self.items_queue = items_queue
        self.verbosity = verbosity
        self.kv_cont = kv_cont

    def run(self):
        while not self.kv_cont.work_finished():
            logging.info_plus("Queue monitor - read = {}, written = {}".format(self.items_queue.insert_count(),
                                                                               self.items_queue.removed_count()))
            self.kv_cont.print_status()
            time.sleep(5)
        logging.info_plus("Queue monitor is done... read = {}, written = {}".format(self.items_queue.insert_count(),
                                                                                    self.items_queue.removed_count()))


class Reader(threading.Thread):

    def __init__(self,
                 s,
                 url,
                 slice_num,
                 total_slices,
                 items_queue,
                 kv_cont,
                 verbosity=0):
        threading.Thread.__init__(self)
        self.s = s
        self.url = url
        self.slice = slice_num
        self.total_slices = total_slices
        self.items_queue = items_queue
        self.kv_cont = kv_cont
        self.verbosity = verbosity

        self.kv_cont.register_reader()

    def run(self):

        read_request = dict()
        read_request["AttributesToGet"] = "*"
        read_request["Segment"] = self.slice
        read_request["TotalSegment"] = self.total_slices

        # Connection : keep-alive will tell requests to use connection pooling, which is good.
        read_headers = dict()
        read_headers["X-v3io-function"] = "GetItems"
        read_headers["Connection"] = "keep-alive"

        total_items = 0

        error_encountered = False

        while not error_encountered:
            # marker will get updated if needed
            read_request_json = json.dumps(read_request)

            read_json_result = {}
            retries_left = 3
            while True: # will break upon success
                try:
                    read_json_result = self.s.put(self.url, data=read_request_json, headers=read_headers, timeout=3.0)
                    break
                except requests.Timeout as e:
                    logging.info_plus("Reader timed out, {} retries left: {}".format(retries_left, e))
                    retries_left = retries_left - 1
                    if retries_left == 0:
                        logging.critical("Exiting Reader - maximum number of retries exceeded")
                        error_encountered = True
                        break
                    else:
                        time.sleep(6 - retries_left)
                except requests.ConnectionError as e:
                    logging.info("Error establishing connection: " + str(e))
                    logging.info("Request: url {}; data {}; headers {};".format(self.url, read_request_json, read_headers))
                    logging.info("Returned: read_json_result {};".format(read_json_result))
                    error_encountered = True
                    break
                except Exception as e:
                    logging.info("Error establishing connection: " + str(e))
                    logging.info("Request: url {}; data {}; headers {};".format(self.url, read_request_json, read_headers))
                    logging.info("Returned: read_json_result {};".format(read_json_result))
                    error_encountered = True
                    break

            if error_encountered or read_json_result is None or read_json_result.status_code != requests.codes.ok:
                logging.critical("Error while reading items")
                break
            else:
                # push items into queue
                read_result = json.loads(read_json_result.content)
                num_of_items = read_result["NumItems"]

                for i in range(0, num_of_items):
                    self.items_queue.put(read_result["Items"][i])
                    total_items = total_items + 1

                # prepare next read request, or finish
                if read_result["LastItemIncluded"] == "FALSE":
                    read_request["Marker"] = read_result["NextMarker"]
                else:
                    logging.info_plus("Reader #{} completed, {} records processed".format(self.slice, total_items))
                    break
        self.kv_cont.de_register_reader()

class Writer(threading.Thread):

    def __init__(self,
                 s,
                 base_url,
                 instance,  # mainly for debug
                 items_queue,
                 kv_cont,
                 verbosity=0):
        threading.Thread.__init__(self)
        self.s = s
        self.base_url = base_url
        self.instance = instance
        self.items_queue = items_queue
        self.kv_cont = kv_cont
        self.verbosity = verbosity

        self.kv_cont.register_writer()

    def run(self):

        # Connection : keep-alive will tell requests to use connection pooling, which is good.
        write_headers = dict()
        write_headers["X-v3io-function"] = "PutItem"
        write_headers["Connection"] = "keep-alive"

        startup_retries = 3
        while not self.kv_cont.readers_launched():
            startup_retries = startup_retries - 1
            if startup_retries == 0:
                self.kv_cont.de_register_writer()
                logging.debug("Writer quit due to initail lack of data...")
                return
            time.sleep(2.0)

        items_written = 0
        error_encountered = False
        while not error_encountered:  # While there are items to write

            curr_item = self.items_queue.get()

            # if queue is empty, need to figure out if work is completed, or need to wait for more
            if curr_item is None:
                if self.kv_cont.readers_done():
                    logging.info_plus("Writer {} is done, {} items written".format(self.instance, items_written))
                    break
                else:
                    logging.debug("Writer {} has no data to work on, but readers are not done..."
                                  " sleeping".format(self.instance))
                    time.sleep(5.0)

            else:
                # Convert record to writeable form
                url = self.base_url + curr_item["__name"]["S"]
                item = dict()
                item["Item"] = curr_item
                item["Item"].pop("__name")
                json_item = json.dumps(item)

                write_json_result = {}
                retries_left = 7
                while True:  # for retries
                    try:
                        write_json_result = self.s.put(url, data=json_item, headers=write_headers, timeout=5.0)
                        items_written = items_written + 1
                        break
                    # TODO: Missing de_register handling on errors.
                    except requests.Timeout as e:
                        logging.info_plus("Writer timed out, {} retries left: {}".format(retries_left, e))
                        retries_left = retries_left - 1
                        if retries_left == 0:
                            logging.critical("Exiting Writer - maximum number of retries exceeded")
                            error_encountered = True
                            break
                        else:
                            time.sleep(20 - retries_left)
                    except requests.ConnectionError as e:
                        logging.info("Error establishing connection: " + str(e))
                        logging.info("Request: url {}; data {}; headers {};".format(url, json_item, write_headers))
                        logging.info("Returned: write_json_result {};".format(write_json_result))
                        error_encountered = True
                        break
                    except Exception as e:
                        logging.info("Error establishing connection: " + str(e))
                        logging.info("Request: url {}; data {}; headers {};".format(url, json_item, write_headers))
                        logging.info("Returned: write_json_result {};".format(write_json_result))
                        error_encountered = True
                        break

                if error_encountered or write_json_result is None or write_json_result.status_code != requests.codes.no_content:
                    logging.critical("Error while writing items")
                    break  # from processing loop

        # orderly exit
        self.kv_cont.de_register_writer()


def main():
    args = parse_arguments()

    add_logging_level(INFO_PLUS_LEVEL_NAME, INFO_PLUS_LOG_LEVEL)

    if args.verbose >= 2:
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.DEBUG)
    elif args.verbose == 1:
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.INFO_PLUS)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.INFO)

    # Suppress other modules:
    logging.getLogger("requests").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    logging.debug("Program arguments after parsing and processing:")
    logging.debug(args)

    protocol = "https" if args.secure else "http"

    source_url = protocol + "://" + args.source_ip + ":" + str(args.port) + "/" \
                 + args.source_container + "/" + args.source_table_path + "/"

    destination_url = protocol + "://" + args.destination_ip + ":" + str(args.port) + "/" \
                      + args.destination_container + "/" + args.destination_table_path + "/"

    logging.info_plus("Source: {}; Destination: {}".format(source_url, destination_url))

    ss = requests.Session()
    sd = requests.Session()
    if args.user is not None and args.password is not None:
        ss.auth = (args.user, args.password)
        sd.auth = (args.user, args.password)

    if args.secure:
        ss.verify = False
        sd.verify = False
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    kv_controller = CopyKvController()

    items_queue = ItemsQueue()
    items_queue_monitor = ItemsQueueMonitor(items_queue, args.verbose, kv_controller)
    items_queue_monitor.start()

    readers = [{} for _ in range(args.source_segments)]
    for i in range(0, args.source_segments):
        readers[i] = Reader(ss,
                            source_url,
                            slice_num=i,
                            total_slices=args.source_segments,
                            items_queue=items_queue,
                            kv_cont=kv_controller,
                            verbosity=args.verbose)
        readers[i].start()

    writers = [{} for _ in range(args.destination_parallelism)]
    for i in range(0, args.destination_parallelism):
        writers[i] = Writer(sd,
                            base_url=destination_url,
                            instance=i,
                            items_queue=items_queue,
                            kv_cont=kv_controller,
                            verbosity=args.verbose)
        writers[i].start()


main()
