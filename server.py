import socket
import json
from urllib.parse import urlparse, parse_qs
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8080
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()
print(f"Server is running at http://{HOST}:{PORT}")

while True:
    connection = server.accept()
    client = connection[0]
    address = connection[1]
    request = b""
    while b"\r\n\r\n" not in request:
        data = client.recv(1024)
        if not data:
            break
        request += data
    if not request:
        client.close()
        continue

    headers_end = request.find(b"\r\n\r\n")
    headers_data = request[:headers_end]
    body = request[headers_end + 4:]
    lines = headers_data.decode("utf-8").split("\r\n")
    first_line = lines[0].split(" ")
    method = first_line[0]
    path = first_line[1]
    version = first_line[2]
    headers = {}

    for line in lines[1:]:
        if ":" in line:
            parts = line.split(":", 1)
            name = parts[0]
            value = parts[1]
            headers[name.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", 0))

    while len(body) < content_length:
        data = client.recv(1024)
        if not data:
            break
        body += data

    parsed_url = urlparse(path)
    route = parsed_url.path
    query = parse_qs(parsed_url.query)

    if method == "GET":
        if route == "/headers":
            response_body = json.dumps(headers, indent=2).encode("utf-8")
            status = "200 OK"
            content_type = "application/json"
        elif route == "/page":
            if "id" in query:
                page_id = query["id"][0]
            else:
                page_id = "none"
            response_body = f"Page id:{page_id}".encode("utf-8")
            status = "200 OK"
            content_type = "text/html; charset=utf-8"
        else:
            if route == "/":
                route = "/index.html"

            base_path = Path(".").resolve()
            file_path = (base_path / route.lstrip("/")).resolve()

            if base_path not in file_path.parents:
                response_body = b"Forbidden"
                status = "403 Forbidden"
                content_type = "text/plain"

            elif file_path.is_file():
                response_body = file_path.read_bytes()
                status = "200 OK"

                if route.endswith(".css"):
                    content_type = "text/css"
                else:
                    content_type = "text/html; charset=utf-8"

            else:
                response_body = b"File not found"
                status = "404 Not Found"
                content_type = "text/plain"
    elif method == "POST":

        if route == "/data":
            try:
                json_data = json.loads(body.decode("utf-8"))
                response_body = json.dumps(json_data).encode("utf-8")
                status = "200 OK"
                content_type = "application/json"

            except (ValueError, UnicodeDecodeError):
                response_body = b'{"Error": "Invalid JSON"}'
                status = "400 Bad Request"
                content_type = "application/json"
        else:
            response_body = b"Not Found"
            status = "404 Not Found"
            content_type = "text/plain"
    else:
        response_body = b"Method Not Allowed"
        status = "405 Method Not Allowed"
        content_type = "text/plain"

    response = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(response_body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8") + response_body
    client.sendall(response)
    client.close()