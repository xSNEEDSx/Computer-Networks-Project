# ClientProgram.py

import socket
import os
import hashlib

HOST = 'localhost'
PORT = 4450
SIZE = 1024
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "LOGOUT"


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    print(client_socket.recv(SIZE).decode(FORMAT))  # Welcome message

    current_dir = ""  # Track current directory

    # Authentication process
    authenticated = False
    while not authenticated:
        username = input("Enter username: ")
        password = input("Enter password: ")
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        client_socket.send(username.encode(FORMAT))
        client_socket.send(hashed_password.encode(FORMAT))
        response = client_socket.recv(SIZE).decode(FORMAT)
        if response.startswith("AUTH_OK"):
            print(response.split('@')[1])
            authenticated = True
        else:
            print(response.split('@')[1])

    # Command loop
    while True:
        command = input(f"Current directory: {current_dir}\nEnter command (DIR, UPLOAD, DOWNLOAD, DELETE, LOGOUT, SUBFOLDER, CD): ").strip()

        if command == "LOGOUT":
            client_socket.send(DISCONNECT_MESSAGE.encode(FORMAT))
            break

        elif command == "UPLOAD":
            filepath = input("Enter filepath to upload (or type BACK to cancel): ").strip()
            if filepath.upper() == "BACK":
                continue
            if not filepath:
                print("Filepath cannot be empty.")
                continue
            filename = os.path.basename(filepath)
            if not os.path.isfile(filepath):
                print(f"File not found: {filepath}")
                continue

            # Send the upload command with the filename to the server
            client_socket.send(f"UPLOAD {filename}".encode(FORMAT))
            response = client_socket.recv(SIZE).decode(FORMAT)
            if response.startswith("EXISTS@"):
                overwrite_prompt = response.split('@')[1]
                overwrite = input(overwrite_prompt + " ").strip().upper()  # Avoid redundant '(YES/NO)'
                if overwrite != "YES":
                    client_socket.send("NO".encode(FORMAT))
                    cancel_response = client_socket.recv(SIZE).decode(FORMAT)  # Process server's cancel response
                    if cancel_response.startswith("CANCEL@"):
                        print(cancel_response.split('@')[1])
                    continue  # Return to the main loop

                client_socket.send("YES".encode(FORMAT))

            elif response.startswith("ERROR@"):
                print(response.split('@')[1])
                continue

            # Proceed with uploading the file
            try:
                with open(filepath, 'rb') as f:
                    while True:
                        file_data = f.read(SIZE)
                        if not file_data:
                            break
                        client_socket.send(file_data)
                    client_socket.send(b"END")  # Signal end of file
                response = client_socket.recv(SIZE).decode(FORMAT)
                print(response.split('@')[1])  # Print success or error message
            except Exception as e:
                print(f"Error during file upload: {e}")

        elif command.startswith("DOWNLOAD"):
            filename = input("Enter filename to download: ").strip()
            client_socket.send(f"DOWNLOAD {filename}".encode(FORMAT))
            try:
                if not filename:
                    print("Filepath cannot be empty.")
                    continue
                filename = os.path.basename(filename)
                if not os.path.isfile(filename):
                    print(f"File not found: {filename}")
                    continue
                with open(filename, 'wb') as f:  # Write in binary mode
                    while True:
                        file_data = client_socket.recv(SIZE)
                        if file_data.endswith(b"END"):  # Check if the data ends with 'END'
                            f.write(file_data[:-len(b"END")])  # Write everything except 'END'
                            break
                        f.write(file_data)  # Write the data chunk
                print("File downloaded successfully.")
            except Exception as e:
                print(f"Error during file download: {e}")

        elif command.startswith("DELETE"):
            filename = input("Enter filename to delete (or type BACK to cancel): ").strip()
            if filename.upper() == "BACK":
                continue

            client_socket.send(f"DELETE {filename}".encode(FORMAT))
            print(client_socket.recv(SIZE).decode(FORMAT))

        elif command == "DIR":
            client_socket.send(command.encode(FORMAT))
            response = client_socket.recv(SIZE).decode(FORMAT)
            print(response.split('@')[1])

        elif command.startswith("SUBFOLDER"):
            action = input("Enter action (create/delete): ").strip()
            folder_path = input("Enter folder path (or type BACK to cancel): ").strip()
            if folder_path.upper() == "BACK":
                continue

            client_socket.send(f"Subfolder {action} {folder_path}".encode(FORMAT))
            print(client_socket.recv(SIZE).decode(FORMAT))

        elif command.startswith("CD"):
            dir_name = input("Enter directory name to change to (or type BACK to cancel): ").strip()
            if dir_name.upper() == "BACK":
                continue

            if not dir_name:
                print("Directory name cannot be empty.")
                continue

            client_socket.send(f"CD {dir_name}".encode(FORMAT))
            response = client_socket.recv(SIZE).decode(FORMAT)
            if response.startswith("CD_OK"):
                current_dir = response.split('@')[1].replace("Changed directory to ", "")
                print(f"Changed directory to {current_dir}")
            else:
                print(response.split('@')[1])

        else:
            print("Invalid command.")

    client_socket.close()


if __name__ == "__main__":
    main()
