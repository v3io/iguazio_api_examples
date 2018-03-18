#!/usr/bin/python

import requests
import igz_nosql_web
import argparse
import httplib

#
# Takes the output of a single record from a getItems call and build the content of .#schema
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
        try: # unsupported data types will cause an exception
            # Convert getItems data types to .#schema data types
            attr_type = TRANSLATE_TYPES[next(iter(attributes_json[attr]))]

            # list item separation handling
            if not first_record:
                output_json += ","
            else:
                first_record = False

            # add current attribute to output json
            output_json = output_json + "{\"name\":\"" + attr + "\",\"type\":\"" + attr_type + "\",\"nullable\":false}"
        except KeyError as e:
            print("Datatype " + str(e) + " not supported, skipping")

    # close output jason, and return
    output_json += "]}"
    if verbose >= 1:
        print(".#schema content:")
        print (output_json)

    return(output_json)

#
# go over all records returned by getItems, and validate they have the same attributes and the same types
def validate_consistency(response_list, verbosity=0):
    error_found = False
    records_counter = 0
    field_counters = {}
    type_validator = {}
    for record in response_list:
        records_counter += 1
        for attribute in record:

            # no need to validate internal attributes, as all objects should have them
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
                print ("validate_consistency: " + str(records_counter) + " records processed")

    # check that all fields appear the same number of times
    field_counter_value = -1
    for field in field_counters:
        if field_counter_value == -1:
            field_counter_value = field_counters.get(field)
        elif field_counter_value != field_counters.get(field):
            print("inconsistency found on the counter of field " + str(field))
            error_found = True
        # else field_counter_value == field_counters.get(field) ==> all is well

    if records_counter != field_counter_value:
        print("inconsistency found on the amount of records, expecting " + str(records_counter) + " got " + str(field_counter_value))
        error_found = True

    # dump info until error found (until verbosity is fixed)
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
        description="Scans a table, and based on the records found, builds and stores the .#schema file for the table")

    parser.add_argument("-i", "--ip",
                        type = str,
                        required = True,
                        help = "IP address of the target")
    parser.add_argument("-p", "--port",
                        type = int,
                        default = -1,
                        required = False,
                        help = "TCP port of the target. Default is 8081 for http and 8443 for https")
    parser.add_argument("-c", "--container",
                        type = str,
                        required = True,
                        help = "Container name or container ID holding the table")
    parser.add_argument("-t", "--table-path",
                        type = str,
                        required = True,
                        help = "Path of the table within the container. Up to two levels are supported")
    parser.add_argument("-r", "--table-root",
                        type = str,
                        required = False,
                        help = "Root of the table (on the same container). Useful in case of partitioning")
    parser.add_argument("-s", "--secure",
                        action = "store_true",
                        required = False,
                        help = "Use https instead of http (without a certificate verification)")
    parser.add_argument("-u", "--user",
                        type = str,
                        required = False,
                        help = "User name if authentication is needed. Must be provided with a password using the -w parameter")
    parser.add_argument("-w", "--password",
                        type = str,
                        required = False,
                        help = "Password if authentication is needed. Must be provided with a user name using the -u parameter")
    parser.add_argument("-l", "--limit",
                        type = int,
                        default = 10,
                        help = "Limit the number of records scanned. Default is 10. Non-positive value means no limit (full table scan)")
    parser.add_argument("-n", "--virtual-nodes",
                        type = int,
                        default = 36,
                        help = "Define execution parallelism")
    parser.add_argument("-d", "--dry-run",
                        action = "store_true",
                        required = False,
                        help = "Dry run. Don't write output file")
    parser.add_argument("-v", "--verbose",
                        action = "count",
                        default = 0,
                        help = "Increase the verbosity of output")
    args = parser.parse_args()
    # custom parameter handling
    if args.port == -1: # if port not specified, assign port defaults based on value of "secure"
        if args.secure:
            args.port = DEF_HTTPS_PORT
        else:
            args.port = DEF_HTTP_PORT

    args.table_root = args.table_path if args.table_root is None else args.table_root

    if (args.user is None and args.password is not None) or (args.user is not None and args.password is None):
        parser.error("User and password must both be provided if one is provided")

    return args;

SCHEMA_FILE_NAME = ".%23schema"

def main():
    args = parse_arguments()

    if args.verbose >= 2:
        print("Program arguments after parsing and processing:")
        print(args)

    protocol = "https" if args.secure else "http"

    base_url = protocol + "://" + args.ip + ":" + str(args.port)
    path = "/" + args.container + "/" + args.table_path + "/"

    if args.verbose >= 1:
        print("Base url: " + str(base_url) + ", path: " + str(path))

    s = requests.Session()
    if args.user is not None and args.password is not None:
        s.auth = (args.user, args.password)

    if args.secure:
        s.verify = False
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    response_list = igz_nosql_web.ngx_get_items_request_parallel(s, base_url, path, limit_amount=args.limit, exp_attrs=["*"], parallelism=args.virtual_nodes, verbose=args.verbose)

    if response_list is None:
        print("Program aborted due to errors")
        exit(1)

    if not response_list: # empty list
        print("Program could not fine any records in the table")
        exit(1)

    if validate_consistency(response_list, verbosity=args.verbose):
        print("Records are consistent")
    else:
        print("Records are not consistent")

    output_json = build_schema_from_item_json_list(response_list[0], args.verbose)

    if not args.dry_run:
        put_res = igz_nosql_web.ngx_put_object(s, base_url, path, SCHEMA_FILE_NAME, output_json)
        if put_res.status_code != requests.codes.ok and put_res.status_code != requests.codes.no_content:
            print(
            "Error encountered while writing .#schema file. Code: " + str(put_res.status_code) + ". Description: " + str(httplib.responses[put_res.status_code]))
        exit(1)
    else:
            print("Dry run - not writing schema")
    exit(0)

main()