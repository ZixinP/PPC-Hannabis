import socket
import select
import Class as cl
import time
import multiprocessing as mp
import signal
import sys

# color = ['red', 'blue', 'green', 'yellow', 'white'] 
# key = 111

def signal_handler(sig, frame):
    print('Received signal to quit. Exiting...')
    for game_proc in games:
        game_proc.terminate()
  
    server_socket.close()
    sys.exit(0)

def main():
    global server_socket
    global games

    signal.signal(signal.SIGINT, signal_handler)

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
                game_proc = mp.Process(target=Game.start_game, args=(color,))
                game_proc.start()
                games.append(game_proc)
                players = []
                start_time = None



if __name__ == "__main__":
    main()

                
