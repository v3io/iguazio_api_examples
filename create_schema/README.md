# create_schema

- [Overview](#overview)
- [Notes](#notes)
- [Usage Examples](#usage-examples)
- [Change Log](#change-log)
- [Known Limitations](#known-limitations)

## Overview

**create_schema** is a Python command-line interface (CLI) utility for automatic creation of a schema file that describes the structure of a NoSQL table.
The utility scans items in a given table, identifies the items' attributes (columns), validates attributes consistency across all scanned items, and creates the schema file based on the attributes of one of the scanned items.

Run `./create_schema --help` for full usage instructions.

## Notes

* The utility creates a **.#schema** JSON file in the root directory of the scanned table.
  This file is used by the [Iguazio Continuous Data Platform](https://www.iguazio.com) to support table reads using Spark DataFrames and Presto.

  > **Note:** Do not rename the generated **.#schema** file.
* The utility scans the configured amount of items (see the `-l | --limit` option) and checks for consistency in the item attributes.
  The schema is created based on the first scanned item.
  In the event of an inconsistency in the identified attributes, a warning message is displayed in the output.

## Usage Examples

Following are some examples for executing the **create_schema** application:

1.  Set only the mandatory `--container` and `--table-path` options and rely on the default IP address (`127.0.0.1` = `localhost`), which assumes that the web-gateway service is running on the same machine as **create_schema**:

    ```sh
    ./create_schema --container bigdata --table-path mytable
    ```

2.  Use the `--ip` and `--port` options to define the IP address and port of the web-gateway service, the `--secure` option to use HTTPS, and the `--limit` option to define the maximum number of table items to scan:

    ```sh
    ./create_schema --ip 192.168.5.123 --port 8445 --container mycontainer --table-path table1 -secure -limit 1
    ```

3.  Use the same options as in example #2, and in addition use the `--user` and `--password` options to define login credentials for HTTP authentication:

    ```sh
    ./create_schema --ip 192.168.5.123 --port 8445 --container mycontainer --table-path mytable -secure -limit 1 --user myuser --password mypass123
    ```

## Change Log

### Version 1.1

This version supports all features of the previous version, as well as the following improvements:

* Change multiple command-line arguments to improve usability.
* TODO: add version information to command-line arguments.

### Version 1.0

* All features are supported via command-line arguments.
* Supports HTTP and HTTPS over default and custom ports.
* Supports operations either with our without user authentication.
* Supports partitioning by allowing to specify a different path for the output file.
* Supports multiple parallel of NoSQL requests for optimal performance.
* Supports dry-run &mdash; the schema file isn't written.

## Known Limitations

* The schema file supports the following attribute types &mdash; `boolean`, `double`, `long`, `null`, and `string`.
  Use `double` also for `float`, and use `long` also for `integer` and `short`.
  The platform converts `float` values to `double` and `short` and `integer` values to `long`.
  > **Note:** The `null` type matches the Spark DataFrames `NullType` type.
  > There's no similar type in Presto.
* Table-item attributes (columns) of type `double` appear as `long` in the **.#schema** file because it's not possible to distinguish between `long` and `double` using `GetItems` calls.
  You can manually edit the **.#schema** file in the table's root directory to change the `type` value of relevant attribute objects in the `fields` array from `"long"` to `"double"`.
* The warning message in the event of inconsistent item attributes is currently not sufficiently informative.
* If non-item files, which do not define any attributes, are present in the scanned directory, they might be used for the creation of the schema file or cause an inconsistent-attributes warning.

