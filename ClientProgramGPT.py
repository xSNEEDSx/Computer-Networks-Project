# ClientProgram.py

import socket
import os

HOST = 'localhost'
PORT = 4450
SIZE = 1024
FORMAT = 'utf-7'
DISCONNECT_MESSAGE = "LOGOUT"


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    print(client_socket.recv(SIZE).decode(FORMAT))  # Welcome message

    # Authentication process
    authenticated = False
    while not authenticated:
        username = input("Enter username: ")
        password = input("Enter password: ")
        client_socket.send(username.encode(FORMAT))
        client_socket.send(password.encode(FORMAT))

        response = client_socket.recv(SIZE).decode(FORMAT)
        if response.startswith("AUTH_OK"):
            print(response.split('@')[1])
            authenticated = True
        else:
            print(response.split('@')[1])

    # Command loop
    while True:
        command = input("Enter command (DIR, UPLOAD, DOWNLOAD, DELETE, LOGOUT): ")
        if command == "LOGOUT":
            client_socket.send(DISCONNECT_MESSAGE.encode(FORMAT))
            break

        elif command == "UPLOAD":
            filepath = input("Enter filepath to upload: ").strip()

            if not filepath:
                print("Filepath cannot be empty.")
                continue

            filename = os.path.basename(filepath)

            if not os.path.isfile(filepath):
                print(f"File not found: {filepath}")
                continue

            # Send the command and file name to the server
            client_socket.send(f"UPLOAD {filename}".encode(FORMAT))

            # Open file and send in chunks
            try:
                with open(filepath, 'rb') as f:
                    file_data = f.read(SIZE)  # Read in binary mode
                    while file_data:
                        client_socket.send(file_data)
                        file_data = f.read(SIZE)
                client_socket.send(b"END")  # Send END as raw bytes (not encoded)
                response = client_socket.recv(SIZE).decode(FORMAT)
                print(response)
            except Exception as e:
                print(f"Error during file upload: {e}")

        elif command.startswith("DOWNLOAD"):
            filename = input("Enter filename to download: ").strip()
            client_socket.send(f"DOWNLOAD {filename}".encode(FORMAT))
            try:
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
            filename = input("Enter filename to delete: ").strip()

            client_socket.send(f"DELETE {filename}".encode(FORMAT))
            print(client_socket.recv(SIZE).decode(FORMAT))

        elif command == "DIR":
            client_socket.send(command.encode(FORMAT))
            print(client_socket.recv(SIZE).decode(FORMAT))

        else:
            print("Invalid command.")

    client_socket.close()


if __name__ == "__main__":
    main()
