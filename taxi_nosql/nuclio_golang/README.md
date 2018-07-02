# Nuclio Example

A Nuclio GO function that

- Accepts a driver event.
- Writes the event to a NoSQL ("KV") table using the DataFrame-like API.

The function should be deployed to a Nuclio instance.

The Python script will push driver events through the Nuclio function.

The `BASE_URL` should be edited according to the Nuclio function IP and port.

