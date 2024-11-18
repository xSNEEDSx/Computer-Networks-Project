# ServerProgram.py

import socket
import threading
import os
import hashlib
from AnalysisProgram import log_operation

HOST = 'localhost'
PORT = 4450
SIZE = 1024
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "LOGOUT"
AUTH_CREDENTIALS = {"Logan": "Baller",
                    "Billy": "Balling",
                    "Robert": "Balla"}

# Directory for file operations
BASE_DIR = 'server_data'
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)


def handle_client(conn, addr):
    log_operation("CONNECT", f"Client connected from {addr}")
    print(f"[NEW CONNECTION] {addr} connected.")
    conn.send("OK@Welcome to the server".encode(FORMAT))

    authenticated = False
    current_dir = BASE_DIR  # Initialize current directory to the base directory

    try:
        while not authenticated:
            username = conn.recv(SIZE).decode(FORMAT)
            hashed_password = conn.recv(SIZE).decode(FORMAT)
            stored_password = AUTH_CREDENTIALS.get(username)

            if stored_password and hashlib.sha256(stored_password.encode()).hexdigest() == hashed_password:
                conn.send("AUTH_OK@Welcome!".encode(FORMAT))
                authenticated = True
                log_operation("AUTH", f"User '{username}' authenticated successfully.")
            else:
                conn.send("AUTH_FAIL@Invalid credentials, try again.".encode(FORMAT))
                log_operation("AUTH_FAIL", f"Failed authentication attempt for user '{username}'.")

        while True:
            command = conn.recv(SIZE).decode(FORMAT)

            if command == DISCONNECT_MESSAGE:
                log_operation("DISCONNECT", f"Client {addr} disconnected.")
                print(f"Connection closed by {addr}")
                break

            elif command == "DIR":
                files = os.listdir(current_dir)
                response = "DIR_OK@" + ", ".join(files)
                conn.send(response.encode(FORMAT))
                log_operation("DIR", f"Listed files for {addr}.")

            elif command.startswith("UPLOAD"):
                parts = command.split(maxsplit=1)
                if len(parts) != 2:
                    conn.send("ERROR@Invalid UPLOAD command format.".encode(FORMAT))
                    continue

                filename = parts[1].strip()
                filepath = os.path.join(BASE_DIR, filename)

                # Check if the file already exists
                if os.path.exists(filepath):
                    conn.send("EXISTS@File already exists. Overwrite? (YES/NO)".encode(FORMAT))
                    response = conn.recv(SIZE).decode(FORMAT).strip().upper()
                    if response != "YES":
                        conn.send("CANCEL@Upload cancelled by user.".encode(FORMAT))  # Use CANCEL@
                        log_operation("UPLOAD_CANCEL", f"Upload attempt for '{filename}' cancelled by user: {addr}")
                        continue

                else:
                    conn.send("READY@Proceed with upload.".encode(FORMAT))
                # Receive the file data
                try:
                    with open(filepath, 'wb') as f:
                        while True:
                            file_data = conn.recv(SIZE)
                            if file_data.endswith(b"END"):  # Check for END marker
                                f.write(file_data[:-len(b"END")])  # Write everything except END
                                break
                            f.write(file_data)
                    conn.send(f"SUCCESS@File '{filename}' uploaded successfully.".encode(FORMAT))
                    log_operation(f"File uploaded: {filename}", addr)
                except Exception as e:
                    conn.send(f"ERROR@{str(e)}".encode(FORMAT))
                    log_operation(f"Error during upload of '{filename}': {str(e)}", addr)  # Log the error

            elif command.startswith("DOWNLOAD"):
                parts = command.split(maxsplit=1)
                if len(parts) != 2:
                    conn.send("ERROR@Invalid DOWNLOAD command format.".encode(FORMAT))
                    continue

                filename = parts[1].strip()
                filepath = os.path.join(BASE_DIR, filename)
                if not os.path.exists(filepath):
                    conn.send(f"ERROR@File '{filename}' not found.".encode(FORMAT))
                    log_operation(f"Failed download: {filename} not found", addr)
                    continue

                try:
                    with open(filepath, 'rb') as f:  # Read in binary mode
                        while True:
                            file_data = f.read(SIZE)
                            if not file_data:
                                break
                            conn.send(file_data)
                        conn.send(b"END")  # Signal the end of the file
                    log_operation(f"File downloaded: {filename}", addr)
                except Exception as e:
                    conn.send(f"ERROR@{str(e)}".encode(FORMAT))

            elif command.startswith("DELETE"):
                filename = command.split(maxsplit=1)[1].strip()
                filepath = os.path.join(BASE_DIR, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    conn.send("DELETE_OK@File deleted successfully.".encode(FORMAT))
                    log_operation("DELETE", f"File '{filename}' deleted by {addr}.")
                else:
                    conn.send("ERROR@File not found.".encode(FORMAT))
                    log_operation("DELETE_FAIL", f"Attempt to delete non-existent file '{filename}'.")

            elif command.startswith("Subfolder"):
                parts = command.split(maxsplit=2)
                action = parts[1].strip().lower()  # Action can be 'create' or 'delete'
                dir_path = parts[2].strip() if len(parts) > 2 else ''
                if action == 'create':
                    full_path = os.path.join(current_dir, dir_path)
                    try:
                        os.makedirs(full_path, exist_ok=True)
                        conn.send("SUBFOLDER_OK@Subfolder created.".encode(FORMAT))
                        log_operation("SUBFOLDER_CREATE", f"Subfolder '{dir_path}' created by {addr}.")
                    except Exception as e:
                        conn.send(f"ERROR@{str(e)}".encode(FORMAT))
                        log_operation("SUBFOLDER_CREATE_FAIL", f"Error creating subfolder '{dir_path}': {e}")

                elif action == "delete":
                    full_path = os.path.join(current_dir, dir_path)
                    try:
                        os.rmdir(full_path)
                        conn.send("SUBFOLDER_OK@Subfolder deleted.".encode(FORMAT))
                        log_operation("SUBFOLDER_DELETE", f"Subfolder '{dir_path}' deleted by {addr}.")
                    except Exception as e:
                        conn.send(f"ERROR@{str(e)}".encode(FORMAT))
                        log_operation("SUBFOLDER_DELETE_FAIL", f"Error deleting subfolder '{dir_path}': {e}")
                else:
                    conn.send("ERROR@Invalid action for subfolder command.".encode(FORMAT))

            elif command.startswith("CD"):  # Change directory command
                try:
                    dir_name = command.split(maxsplit=1)[1].strip()
                    if dir_name == "..":  # Handle moving up one directory
                        # Compute the new directory by going to the parent of the current directory
                        new_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
                        # Ensure the new directory is within the allowed base directory
                        if os.path.commonpath([new_dir, BASE_DIR]) != BASE_DIR:
                            conn.send("ERROR@Cannot move outside the base directory.".encode(FORMAT))
                            log_operation("CD_FAIL", f"Client {addr} attempted to move outside the base directory.")
                        else:
                            current_dir = new_dir  # Update current directory
                            conn.send(f"CD_OK@Changed directory to {current_dir}".encode(FORMAT))
                            log_operation("CD", f"Client {addr} changed directory to {current_dir}.")
                    else:
                        # Handle navigating into a specific subdirectory
                        new_dir = os.path.join(current_dir, dir_name)
                        if os.path.isdir(new_dir):
                            current_dir = os.path.abspath(
                                new_dir)  # Update current directory to the resolved absolute path
                            conn.send(f"CD_OK@Changed directory to {current_dir}".encode(FORMAT))
                            log_operation("CD", f"Client {addr} changed directory to {current_dir}.")
                        else:
                            conn.send("ERROR@Directory not found.".encode(FORMAT))
                            log_operation("CD_FAIL", f"Client {addr} failed to change directory to {dir_name}.")
                except Exception as e:
                    conn.send(f"ERROR@Unexpected error: {str(e)}".encode(FORMAT))
                    log_operation("CD_ERROR", f"Unexpected error occurred: {str(e)}")

            else:
                conn.send("ERROR@Unknown command.".encode(FORMAT))
                log_operation("UNKNOWN_COMMAND", f"Unknown command received from {addr}: {command}")

    except Exception as e:
        log_operation("ERROR", f"Error handling client {addr}: {e}")
    finally:
        conn.close()


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
