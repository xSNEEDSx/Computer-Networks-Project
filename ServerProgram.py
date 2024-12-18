# ServerProgram.py

import socket
import threading
import os
import hashlib
import time
import pandas
import openpyxl
from AnalysisProgram import log_operation  # Importing the log function

HOST = 'localhost'
PORT = 4450
SIZE = 1024
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = 'LOGOUT'
AUTH_CREDENTIALS = {"Logan": "Baller", "Billy": "Balling", "Robert": "Balla"}

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

            # Measure server response time
            response_start_time = time.time()

            if command == "DIR":
                files = os.listdir(current_dir)
                response = "DIR_OK@" + ", ".join(files)
                conn.send(response.encode(FORMAT))
                response_end_time = time.time()
                response_time = response_end_time - response_start_time
                log_operation("SERVER_RESPONSE_TIME", f"Response time for DIR: {response_time:.2f} seconds")
                log_operation("DIR", f"Listed files for {addr}.")

            elif command.startswith("UPLOAD"):
                parts = command.split(maxsplit=1)
                if len(parts) != 2:
                    conn.send("ERROR@Invalid UPLOAD command format.".encode(FORMAT))
                    continue

                filename = parts[1].strip()
                filepath = os.path.join(current_dir, filename)

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

                # Record start time for upload
                upload_start_time = time.time()

                try:
                    with open(filepath, "wb") as f:
                        while True:
                            file_data = conn.recv(SIZE)
                            if file_data.endswith(b"END"):  # Check for END marker
                                f.write(file_data[:-len(b"END")])  # Write everything except END
                                break
                            f.write(file_data)

                    upload_end_time = time.time()
                    upload_time = upload_end_time - upload_start_time + 0.000001  # avoid division by zero

                    # Calculate upload rate (MB/s)
                    file_size = os.path.getsize(filepath)
                    upload_rate = file_size / (1024 * 1024) / upload_time  # MB/s

                    conn.send(f"SUCCESS@File {filename} uploaded successfully.".encode(FORMAT))

                    # Log the performance metrics
                    log_operation(f"File uploaded: '{filename}' at {upload_rate:.2f} MB/s", addr)
                    log_operation("UPLOAD_TIME", f"Upload time: {upload_time:.2f} seconds")
                    log_operation("UPLOAD_RATE", f"Upload rate: {upload_rate:.2f} MB/s")

                    # Append metrics to an Excel file
                    excel_file = "upload_rates.xlsx"
                    data = {
                        "Timestamp": [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(upload_end_time))],
                        "File Name": [filename],
                        "File Size (MB)": [file_size / (1024 * 1024)],  # Convert bytes to MB
                        "Upload Time (s)": [upload_time],
                        "Upload Rate (MB/s)": [upload_rate],
                    }

                    # Create a DataFrame
                    df = pandas.DataFrame(data)

                    # Append to Excel (create file if it doesn't exist)
                    try:
                        # If the file exists, read it and append the new data
                        existing_data = pandas.read_excel(excel_file, engine='openpyxl')
                        updated_data = pandas.concat([existing_data, df], ignore_index=True)
                    except FileNotFoundError:
                        # If the file doesn't exist, create a new one
                        updated_data = df

                    # Save to Excel
                    updated_data.to_excel(excel_file, index=False, engine='openpyxl')
                    print(f"Upload saved successfully to {excel_file}")

                except Exception as e:
                    conn.send(f"ERROR@{str(e)}".encode(FORMAT))
                    log_operation(f"Error during upload of '{filename}': {str(e)}", addr)  # Log the error

            elif command.startswith("DOWNLOAD"):
                parts = command.split(maxsplit=1)
                if len(parts) != 2:
                    conn.send("ERROR@Invalid DOWNLOAD command format.".encode(FORMAT))
                    continue

                filename = parts[1].strip()
                filepath = os.path.join(current_dir, filename)
                if not os.path.isfile(filepath):
                    conn.send("ERROR@File not found.".encode(FORMAT))
                    log_operation("DOWNLOAD_FAIL", f"File not found: '{filename}' requested by {addr}")
                    continue

                try:
                    conn.send("SUCCESS@File found. Starting transfer.".encode(FORMAT))
                    download_start_time = time.time()  # Start timer for performance metrics
                    with open(filepath, "rb") as f:
                        while True:
                            file_data = f.read(SIZE)
                            if not file_data:
                                break
                            conn.send(file_data)
                        conn.send(b"END")  # End marker for file transfer
                    download_end_time = time.time()

                    # Calculate performance metrics
                    download_time = download_end_time - download_start_time + 0.000001  # avoid division by zero
                    file_size = os.path.getsize(filepath)  # Get file size
                    download_rate = file_size / (1024 * 1024) / download_time  # Rate in MB/s

                    # Log performance metrics
                    log_operation("DOWNLOAD_SUCCESS", f"File '{filename}' sent to {addr}")
                    log_operation("DOWNLOAD_TIME", f"Download time: {download_time:.2f} seconds")
                    log_operation("DOWNLOAD_RATE", f"Download rate: {download_rate:.2f} MB/s")

                    # Append metrics to an Excel file
                    excel_file = "download_rates.xlsx"
                    data = {
                        "Timestamp": [time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(download_end_time))],
                        "File Name": [filename],
                        "File Size (MB)": [file_size / (1024 * 1024)],  # Convert bytes to MB
                        "Download Time (s)": [download_time],
                        "Download Rate (MB/s)": [download_rate],
                    }

                    # Create a DataFrame
                    df = pandas.DataFrame(data)

                    # Append to Excel (create file if it doesn't exist)
                    try:
                        # If the file exists, read it and append the new data
                        existing_data = pandas.read_excel(excel_file, engine="openpyxl")
                        updated_data = pandas.concat([existing_data, df], ignore_index=True)
                    except FileNotFoundError:
                        # If the file doesn't exist, create a new one
                        updated_data = df

                    # Save to Excel
                    updated_data.to_excel(excel_file, index=False, engine="openpyxl")
                    print(f"Download saved successfully to {excel_file}")

                except Exception as e:
                    conn.send(f"ERROR@{str(e)}".encode(FORMAT))
                    log_operation("DOWNLOAD_ERROR", f"Error during download of '{filename}': {str(e)}")

            elif command.startswith("DELETE"):
                # Use the delimiter '@@' to split the command and filename
                parts = command.split("@@", maxsplit=1)

                # Check if no filename was provided
                if len(parts) < 2 or not parts[1].strip():
                    conn.send("ERROR@No file inputted for deletion.".encode(FORMAT))
                    log_operation("DELETE_FAIL", "No file inputted for deletion.")
                    continue

                filename = parts[1].strip()
                filepath = os.path.join(current_dir, filename)
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
                if action == "create":
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
                        if os.path.commonpath([os.path.abspath(new_dir), os.path.abspath(BASE_DIR)]) != os.path.abspath(BASE_DIR):
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
                            current_dir = os.path.abspath(new_dir)  # Update current directory to the resolved absolute path
                            conn.send(f"CD_OK@Changed directory to {current_dir}".encode(FORMAT))
                            log_operation("CD", f"Client {addr} changed directory to {current_dir}.")
                        else:
                            conn.send("ERROR@Directory not found.".encode(FORMAT))
                            log_operation("CD_FAIL", f"Client {addr} failed to change directory to {dir_name}.")
                except Exception as e:
                    conn.send(f"ERROR@Unexpected error: {str(e)}".encode(FORMAT))
                    log_operation("CD_ERROR", f"Unexpected error occurred: {str(e)}")

    except Exception as e:
        log_operation("ERROR", f"Error handling client {addr}: {e}")
    finally:
        conn.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()


if __name__ == "__main__":
    start_server()
