import socket
import select
import Class as cl
import time

# color = ['red', 'blue', 'green', 'yellow', 'white'] 
# key = 111

def main():
    HOST = '127.0.0.1'
    PORT = 12345
    color = ['red', 'blue', 'green', 'yellow', 'white']
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
                if len(players) == 3:
                    start_time = time.time()   # when 3 players, start timer
                elif len(players) == 4 or (start_time and time.time() - start_time > 60):  # if 4 players or 60 seconds passed, start game
                    Game = cl.Game(players, color, key)
                    Game.start_game()
                    games.append(Game)
                    players = []
                    
if __name__ == "__main__":
    main()
                