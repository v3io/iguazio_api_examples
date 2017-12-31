Nuclio files that loads driver's data to a KV table

The function in driver_event.go should be deployed to Nuclio instance.
The Python script in insert_driver_nuclio.py will push driver's events through the Nuclio function
    The BASE_URL should be edited according to the Nuclio function IP and port
