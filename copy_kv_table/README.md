# copy_kv_table

- [Overview](#overview)
- [Usage Examples](#usage-examples)
- [Change Log](#change-log)
- [Known Limitations](#known-limitations)

## Overview
**copy_kv_table** is a utility to copy KV records. The utility supports copying between two separate containers/systems, or within the same one.
The utility uses the Iguazio Web-API. 

The utility only copies KV records, and cannot copy files, or file content in case the KV records are layed on files with content.

## Usage Examples
Basic example for *(copy_kv_table**:

```
--source-ip  192.168.1.1 --destination-ip 192.168.1.2 --source-container bigdata --source-table-path customers --destination-table-path customers2 -g 36  --user iguazio --password secret -v -z 16
```
## Change Log

### Version 1.0

* All features are supported via command-line arguments.
* Supports HTTP and HTTPS over default and custom ports.
* Supports operations either with our without user authentication.
* Supports copying between different containers and systems (and within the same system/container).
* Supports multiple parallel of NoSQL requests for optimal performance, with different levels of paralellism

## Known Limitations

* Should add option to use the same destination IP/container as the source if not defined.
* Should add option to provide list of IPs for source/destination for better load balancing.
* In some cases the number of records written is reported as higher than the records read.

