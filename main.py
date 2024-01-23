import socket
import select
import multiprocessing
import signal
import Class as cl

if __name__ == "__main__":
    HOST = "localhost"
    PORT = 6666
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(4)
        client_id = 0
        while True:
            readable, _, _ = select.select([server_socket], [], [], 1)
            if server_socket in readable:
                client_socket, address = server_socket.accept()
                player = cl.Player(client_id, client_socket)
                