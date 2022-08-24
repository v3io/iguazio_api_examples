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
import igz_nosql_web
import argparse
import httplib

#
# Takes the output of a single table item from a GetItems call and builds the content of a JSON .#schema file
def build_schema_from_item_json_list(attributes_json, verbose = 0):
    TRANSLATE_TYPES = {
        "S": "string",
        "N": "long", # Need to manually update output file to "double" if fractions are in this field
        # "TS" : "timestamp", # Tech preview in 1.5, and not supported in Presto on IGZ
        # "B": "blob", not supported in Presto on IGZ
        "BOOL": "boolean"
    }

    if verbose >= 1:
        print("Record used for building the schema file:")
        print(attributes_json)

    output_json = "{\"fields\":["
    first_record = True

    for attr in attributes_json:
        try: # Unsupported data types will cause an exception
            # Convert GetItems data types to .#schema data types
            attr_type = TRANSLATE_TYPES[next(iter(attributes_json[attr]))]

            # List item separation handling
            if not first_record:
                output_json += ","
            else:
                first_record = False

            # Add current attribute to the output JSON schema file
            output_json = output_json + "{\"name\":\"" + attr + "\",\"type\":\"" + attr_type + "\",\"nullable\":false}"
        except KeyError as e:
            print("Datatype " + str(e) + " not supported, skipping")

    # Close the output JSON schema file, and return
    output_json += "]}"
    if verbose >= 1:
        print(".#schema content:")
        print (output_json)

    return(output_json)

#
# Iterate the items returned by GetItems and validate that they have the same attributes names and types
def validate_consistency(response_list, verbosity=0):
    error_found = False
    records_counter = 0
    field_counters = {}
    type_validator = {}
    for record in response_list:
        records_counter += 1
        for attribute in record:

            # No need to validate internal attributes, as all objects should have them
            if str(attribute).startswith("__"):
                continue

            if attribute in field_counters.keys():
                field_counters[attribute] += 1;
                if type_validator[attribute] !=  next(iter(record[attribute])):
                    print("Type inconsistency found on type of field " + str(attribute))
                    error_found = True
            else:
                field_counters[attribute] = 1
                type_validator[attribute] = next(iter(record[attribute]))

        if verbosity >= 2:
            if records_counter % 10000 == 0:
                print ("validate_consistency: " + str(records_counter) + " items processed.")

    # Check that all fields appear the same number of times
    field_counter_value = -1
    for field in field_counters:
        if field_counter_value == -1:
            field_counter_value = field_counters.get(field)
        elif field_counter_value != field_counters.get(field):
            print("inconsistency found on the counter of field " + str(field))
            error_found = True
        # else field_counter_value == field_counters.get(field) ==> all is well

    if records_counter != field_counter_value:
        print("Inconsistency found in the amount of scanned items - expected " + str(records_counter) + ", got " + str(field_counter_value) + ".")
        error_found = True

    # Dump info until an error is found (until verbosity is fixed)
    if error_found:
        print(field_counters)
        print(type_validator)
        return False
    else:
        return True

def parse_arguments():
    DEF_HTTP_PORT = 8081
    DEF_HTTPS_PORT = 8443

    parser = argparse.ArgumentParser(
        description="Creates a .#schema file that describes the structure of a NoSQL table by scanning table items")

    parser.add_argument("-i", "--ip",
                        type = str,
                        default = "127.0.0.1",
                        required = False,
                        help = "IP address of the web-gateway service. Default = 'localhost'.")
    parser.add_argument("-p", "--port",
                        type = int,
                        default = -1,
                        required = False,
                        help = "TCP port of the web-gateway service. Default = 8081 for HTTP and 8443 for HTTPS (see the -s|--secure option).")
    parser.add_argument("-c", "--container",
                        type = str,
                        required = True,
                        help = "The name of the table's parent container.")
    parser.add_argument("-t", "--table-path",
                        type = str,
                        required = True,
                        help = "Path to the table's root directory within the container. Note: For Presto, the table must reside in the container's root directory.")
    parser.add_argument("-r", "--read-partition",
                        type = str,
                        default = "/",
                        required = False,
                        help = "Path to the directory representing the partition to read within the table path. Default = '/' - the table's root directory. ")
    parser.add_argument("-s", "--secure",
                        action = "store_true",
                        required = False,
                        help = "Use HTTPS (without a certificate verification) instead of HTTP.")
    parser.add_argument("-u", "--user",
                        type = str,
                        required = False,
                        help = "Username to be used for HTTP authentication together with the password set with the -w or --password option.")
    parser.add_argument("-w", "--password",
                        type = str,
                        required = False,
                        help = "Password to be used for HTTP authentication together with the username set with the -u or --user option.")
    parser.add_argument("-l", "--limit",
                        type = int,
                        default = 10,
                        help = "The number of table items to scan to determine the schema. A non-positive value means no limit (full table scan). Default = 10.")
    parser.add_argument("-g", "--segments",
                        type = int,
                        default = 36,
                        help = "The number of segments to use in the table-items scan. A value higher than 1 configures a parallel multi-segment scan. Default = 36.")
    parser.add_argument("-d", "--dry-run",
                        action = "store_true",
                        required = False,
                        help = "Perform a dry run: perform the configured table scan, but don't create the output schema file.")
    parser.add_argument("-v", "--verbose",
                        action = "count",
                        default = 0,
                        help = "Increase the verbosity level of the command-line output.")
    args = parser.parse_args()
    # Custom parameter handling
    if args.port == -1: # If port isn't specified, assign port defaults based on the value of "secure"
        if args.secure:
            args.port = DEF_HTTPS_PORT
        else:
            args.port = DEF_HTTP_PORT

    if (args.user is None and args.password is not None) or (args.user is not None and args.password is None):
        parser.error("User and password must both be provided if one is provided.")

    return args;

SCHEMA_FILE_NAME = ".%23schema"

def main():
    args = parse_arguments()

    if args.verbose >= 2:
        print("Program arguments after parsing and processing:")
        print(args)

    protocol = "https" if args.secure else "http"

    base_url = protocol + "://" + args.ip + ":" + str(args.port)
    path_to_write = "/" + args.container + "/" + args.table_path + "/"
    if args.read_partition != "/":
        path = path_to_write + args.read_partition + "/"
    else:
        path = path_to_write

    if args.verbose >= 1:
        print("Base url: " + str(base_url) + ", path: " + str(path) + ", path to write: " + path_to_write)

    s = requests.Session()
    if args.user is not None and args.password is not None:
        s.auth = (args.user, args.password)

    if args.secure:
        s.verify = False
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    response_list = igz_nosql_web.ngx_get_items_request_parallel(s, base_url, path, limit_amount=args.limit, exp_attrs=["*"], parallelism=args.segments, verbose=args.verbose)

    if response_list is None:
        print("Program aborted due to errors.")
        exit(1)

    if not response_list: # empty list
        print("Could not find any items in the table. No schema file was created.")
        exit(1)

    if validate_consistency(response_list, verbosity=args.verbose):
        print("The attributes of the scanned table items are consistent")
    else:
        print("WARNING: The attributes of the scanned table items are not consistent.")

    output_json = build_schema_from_item_json_list(response_list[0], args.verbose)

    if not args.dry_run:
        if args.verbose >= 1:
            print("Schema:")
            print(output_json)

        put_res = igz_nosql_web.ngx_put_object(s, base_url, path_to_write, SCHEMA_FILE_NAME, output_json)
        if put_res.status_code != requests.codes.ok and put_res.status_code != requests.codes.no_content:
            print(
            "Error encountered while writing .#schema file. Code: " + str(put_res.status_code) + ". Description: " + str(httplib.responses[put_res.status_code]))
        exit(1)
    else:
            print("Schema:")
            print(output_json)
            print("WARNING: Dry run - the schema file will not be written.")
    exit(0)

main()

