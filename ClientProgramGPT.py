# ClientProgram.py

import os
import socket
import hashlib  # For hashing passwords
from cryptography.fernet import Fernet

IP = "localhost"
PORT = 4450
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
SERVER_PATH = "server_data"

# Generate a key for symmetric encryption (this should be securely shared with the server)
key = Fernet.generate_key()
cipher = Fernet(key)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def connect(client):
    client.connect(ADDR)
    print("Connected to the server.")


def authenticate(client):
    username = input("Enter username: ")
    password = input("Enter password: ")
    encrypted_password = cipher.encrypt(password.encode(FORMAT))  # Encrypt password

    auth_message = f"AUTH@{username},{encrypted_password.decode(FORMAT)}"
    client.send(auth_message.encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    cmd, msg = response.split("@")
    if cmd == "OK":
        print("Authentication successful.")
    else:
        print("Authentication failed:", msg)
        client.close()
        exit()


def upload(client, file_path):
    if not os.path.isfile(file_path):
        print("File does not exist.")
        return

    file_name = os.path.basename(file_path)
    client.send(f"UPLOAD@{file_name}".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    if response == "EXISTS":
        overwrite = input("File already exists on server. Overwrite? (yes/no): ").strip().lower()
        if overwrite != "yes":
            return
        client.send("OVERWRITE".encode(FORMAT))
    else:
        client.send("PROCEED".encode(FORMAT))

    with open(file_path, "rb") as file:
        while chunk := file.read(SIZE):
            client.send(chunk)
    client.send(b"")  # Signal end of file transfer
    print("File uploaded successfully.")


def download(client, file_name):
    client.send(f"DOWNLOAD@{file_name}".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    if response == "NOTFOUND":
        print("File not found on the server.")
        return

    with open(file_name, "wb") as file:
        while True:
            data = client.recv(SIZE)
            if not data:
                break
            file.write(data)
    print("File downloaded successfully.")


def delete(client, file_name):
    client.send(f"DELETE@{file_name}".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    print(response)


def list_files(client):
    client.send("DIR".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    print("Files on server:\n", response)


def manage_subfolder(client, operation, folder_path):
    client.send(f"SUBFOLDER@{operation} {folder_path}".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    print(response)


def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect and authenticate
    connect(client)
    authenticate(client)

    # Main command loop
    while True:
        data = input("> ").strip()
        if not data:
            continue

        command_parts = data.split(" ")
        cmd = command_parts[0].upper()

        if cmd == "UPLOAD" and len(command_parts) == 2:
            upload(client, command_parts[1])

        elif cmd == "DOWNLOAD" and len(command_parts) == 2:
            download(client, command_parts[1])

        elif cmd == "DELETE" and len(command_parts) == 2:
            delete(client, command_parts[1])

        elif cmd == "DIR":
            list_files(client)

        elif cmd == "SUBFOLDER" and len(command_parts) == 3:
            operation, folder_path = command_parts[1], command_parts[2]
            if operation in {"create", "delete"}:
                manage_subfolder(client, operation, folder_path)
            else:
                print("Invalid subfolder operation. Use 'create' or 'delete'.")

        elif cmd == "LOGOUT":
            client.send("LOGOUT".encode(FORMAT))
            print("Logged out successfully.")
            break

        else:
            print("Invalid command. Available commands: UPLOAD, DOWNLOAD, DELETE, DIR, SUBFOLDER, LOGOUT.")

    print("Disconnected from the server.")
    client.close()


if __name__ == "__main__":
    main()
