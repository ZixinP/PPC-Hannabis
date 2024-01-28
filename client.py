import socket
import sysv_ipc

def main():
    host = '127.0.0.1'
    port = 12345

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    print("Connected to server")

    # 接收服务器发送的消息队列标识符
    queue_id = int(client_socket.recv(1024).decode())
    print(f"Received queue id: {queue_id}")

    # 连接到消息队列
    queue = sysv_ipc.MessageQueue(queue_id)

    # 这里可以编写更多的与服务器交互的代码
    # ...

    client_socket.close()

if __name__ == "__main__":
    main()
