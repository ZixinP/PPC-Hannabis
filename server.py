import socket
import select
import Class as cl
import time

# color = ['red', 'blue', 'green', 'yellow', 'white'] 
# key = 111

def main():
    HOST = '127.0.0.1'
    PORT = 12345
    color = ['red', 'blue', 'green', 'yellow']
    key = 111

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(4)
        games = []
        players = []
        start_time = None
        while True:
            readable, _, _ = select.select([server_socket], [], [], 1)
            if server_socket in readable:
                client_socket, address = server_socket.accept()    # if new client, accept
                print('Connected to player', len(players), 'from', address)
                player = cl.Player(len(players), client_socket)
                players.append(player)

            if len(players) == 3 and start_time is None:
                start_time = time.time()
                print('start time:', start_time)
                start_game_condition = False
            elif len(players) == 3 and start_time is not None and (time.time() - start_time > 60) or len(players) == 4:
              start_game_condition = True
            else:
              start_game_condition = False

            if start_game_condition: 
              Game = cl.Game(players, key)
              Game.start_game(color)
              games.append(Game)
              players = []
              start_time = None

        server_socket.close()
        games = []
        players = []
        start_time = None
            


if __name__ == "__main__":
    main()

                
