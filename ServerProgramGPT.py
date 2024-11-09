import os
import socket
import threading
import hashlib

IP = "localhost"
PORT = 4450
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
SERVER_PATH = "server_data"

USER_CREDENTIALS = {
    "Logan": hashlib.sha256("Baller".encode(FORMAT)).hexdigest(),
    "Robert": hashlib.sha256("Balls".encode(FORMAT)).hexdigest(),
    "Billy": hashlib.sha256("Balling".encode(FORMAT)).hexdigest()
    # Add more users here
}


def handle_client(conn, addr):
    """Handle communication with a single client."""
    print(f"[NEW CONNECTION] {addr} connected.")
    conn.send("OK@Welcome to the server".encode("utf-8"))

    try:
        while True:
            data = conn.recv(SIZE)  # Receive data from client
            if not data:  # If no data is received, the client may have disconnected
                print(f"Connection closed by {addr}")
                break

            data = data.decode(FORMAT)  # Decode the received bytes to string
            print(f"Data received: {data}")

            cmd_data = data.split("@")
            cmd = cmd_data[0]

            # Handle authentication (check hashed password)
            if cmd == "AUTH":
                if len(cmd_data) < 3:
                    conn.send("AUTH_FAILED@Missing arguments".encode("utf-8"))
                    continue

                username, password_hash = cmd_data[1], cmd_data[2]
                print(f"Received password hash: {password_hash}")  # Debugging
                if USER_CREDENTIALS.get(username) == password_hash:
                    print("Authentication successful.")
                    conn.send("AUTH_OK".encode("utf-8"))
                else:
                    print("Authentication failed.")
                    conn.send("AUTH_FAILED".encode("utf-8"))

            elif cmd == "LOGOUT":
                print(f"{addr} logged out.")
                break

            # Add other command logic here (e.g., file upload/download)

    except Exception as e:
        print(f"Error while handling client {addr}: {e}")
        conn.send(f"ERROR@{e}".encode("utf-8"))  # Send error to the client

    finally:
        print(f"{addr} disconnected")
        conn.close()


def start_server():
    """Start the server."""
    host = 'localhost'
    port = 4450

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")

    while True:
        try:
            conn, addr = server_socket.accept()
            print(f"[NEW CONNECTION] {addr} connected.")
            handle_client(conn, addr)
        except Exception as e:
            print(f"Error accepting client connection: {e}")


if __name__ == "__main__":
    start_server()
