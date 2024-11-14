# ServerProgram.py
import socket
import threading
import os

HOST = 'localhost'
PORT = 4450
SIZE = 1024
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "LOGOUT"
AUTH_CREDENTIALS = {"Logan": "Baller",
                    "Billy": "Balling",
                    "Robert": "Balla"}  # Example credentials

# Directory for file operations
BASE_DIR = 'server_data'
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)


def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    conn.send("OK@Welcome to the server".encode(FORMAT))

    authenticated = False
    try:
        while not authenticated:
            username = conn.recv(SIZE).decode(FORMAT)
            password = conn.recv(SIZE).decode(FORMAT)
            if AUTH_CREDENTIALS.get(username) == password:
                conn.send("AUTH_OK@Welcome!".encode(FORMAT))
                authenticated = True
            else:
                conn.send("AUTH_FAIL@Invalid credentials, try again.".encode(FORMAT))

        while True:
            command = conn.recv(SIZE).decode(FORMAT)
            if command == DISCONNECT_MESSAGE:
                print(f"Connection closed by {addr}")
                break
            elif command == "DIR":
                try:
                    files = os.listdir(BASE_DIR)
                    response = "DIR_OK@" + ", ".join(files)
                except Exception as e:
                    response = f"ERROR@{str(e)}"
                conn.send(response.encode(FORMAT))

            elif command.startswith("UPLOAD"):
                _, filename = command.split()
                filepath = os.path.join(BASE_DIR, filename)
                with open(filepath, 'wb') as f:
                    while True:
                        file_data = conn.recv(SIZE)
                        if file_data == b"END":
                            break
                        f.write(file_data)
                conn.send("UPLOAD_OK@File uploaded successfully.".encode(FORMAT))

            elif command.startswith("DOWNLOAD"):
                _, filename = command.split()
                filepath = os.path.join(BASE_DIR, filename)
                if os.path.exists(filepath):
                    conn.send("DOWNLOAD_OK@Starting file download.".encode(FORMAT))
                    with open(filepath, 'rb') as f:
                        file_data = f.read(SIZE)
                        while file_data:
                            conn.send(file_data)
                            file_data = f.read(SIZE)
                    conn.send("END".encode(FORMAT))
                else:
                    conn.send("ERROR@File not found.".encode(FORMAT))

            elif command.startswith("DELETE"):
                _, filename = command.split()
                filepath = os.path.join(BASE_DIR, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    conn.send("DELETE_OK@File deleted successfully.".encode(FORMAT))
                else:
                    conn.send("ERROR@File not found.".encode(FORMAT))

            else:
                conn.send("ERROR@Unknown command.".encode(FORMAT))
    except Exception as e:
        print(f"Error while handling client {addr}: {e}")
    finally:
        conn.close()
        print(f"{addr} disconnected")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


start_server()
