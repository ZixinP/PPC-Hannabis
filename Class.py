import multiprocessing as mp
import sysv_ipc
import sys
from random import shuffle
# import signal

# color = ['red', 'blue', 'green', 'yellow'] 
# key = 111

class Game:   
    def __init__(self, players,key):
        self.cards = []
        self.players = players
        self.suits={}
        self.round = 0
        self.turn = 0
        self.self_lock = mp.Lock()
        self.tokens = len(players) +3
        self.fuses = 3
        self.discards = []
        self.signal = False
        self.win= False
        self.queue_id = key

    # initialize the cards in the deck   
    def init_cards(self,color):
        desk_cards = []
        color_game = color[:len(self.players)]

        # add cards in order 1,1,1,2,2,3,3,4,4,5
        for c in color_game:
            desk_cards.append(Card(c,1))
            for i in range (1,5):
                desk_cards.append(Card(c,i))
                desk_cards.append(Card(c,i))
            desk_cards.append(Card(c,5))
            self.suits[c] = 0   # initialize the number of cards played for each suit

        self.cards = desk_cards

    def shuffle_cards(self):
        shuffle(self.cards)
        for card in self.cards:
          print(f"card: {card.color} {card.number}")

    def distribute_cards(self):
        # distribute cards to players
        for p in self.players:
            for i in range(0,5):
                p.hand[i] = self.cards.pop()


    # update the game status from shared memory to local memory
    def update_game(self, shared_memory):
        self.cards = shared_memory["cards"]
        self.discards = shared_memory["discards"]
        self.suits = shared_memory["suits"]
        self.fuses = shared_memory["fuses"]
        self.tokens = shared_memory["tokens"]


    #check if game is over
    def check_end(self, shared_memory):
        FLAG = True
        if shared_memory["fuses"] == 0:
            self.signal = True
            self.win = False
            return
        else:
            for _,number in shared_memory["suits"].items():
                if number < 5:
                    FLAG = False
            if FLAG:
                self.signal = True
                self.win = True
                return


    # notify players the game ends
    def end_game(self,pipes):
        for pipe_obj in pipes:
            pipe = pipe_obj[1]
            pipe.send("GAME OVER")
            if self.win:
                pipe.send("Congratulations! You win the game")
            else:
                pipe.send("Sorry, you lose the game")
            pipe.close()


    # create a shared memory for all players and start all players' processes
    def set_up_players(self):  
            manager = mp.Manager()
            # create a shared memory for all players, in form of dictionary
            shared_memory = manager.dict()
            shared_memory["queue_id"] = self.queue_id
            shared_memory["tokens"] = self.tokens
            shared_memory["fuses"] = self.fuses
            shared_memory["discards"] = self.discards
            shared_memory["suits"] = self.suits
            shared_memory["cards"] = self.cards
            # collect all players' id
            list_players_id = [p.id for p in self.players]
            shared_memory["players_id"] = list_players_id
            shared_memory["player_cards"] = {p.id: p.hand for p in self.players}

            msg_queue = sysv_ipc.MessageQueue(self.queue_id, sysv_ipc.IPC_CREAT)
            pipes = []
            processes = []
            for p in self.players:
                server_pipe, player_pipe = mp.Pipe()
                pipes.append([p.id, server_pipe])
                p_process = mp.Process(target=p.play, args=(self.self_lock, shared_memory, self.queue_id, player_pipe))
                processes.append(p_process)

            for process in processes:
                process.start()

            return shared_memory, processes, pipes,msg_queue


    # start the game        
    def start_game(self, color):
        print("Game starts")

        self.init_cards(color)
        print("Cards initialized")

        self.shuffle_cards()
        print("Cards shuffled")

        self.distribute_cards()
        print("Cards distributed")

        shared_memory, processes, pipes, msg_queue = self.set_up_players()
        print("Players set up")

        while not self.signal:
                pipe_turn = next(pipe[1] for pipe in pipes if pipe[0] == self.turn)   # find the pipe of the player whose turn it is
                print(f"Player {self.turn}'s turn")
                if pipe_turn:
                    pipe_turn.send("Your turn")
                else:
                    print("Error in finding pipe")      

                action_player = pipe_turn.recv()
                print(action_player)

                end_turn = pipe_turn.recv()
                print(end_turn)
                self.update_game(shared_memory)    # update the game status from shared memory to local memory
                self.turn = (self.turn + 1) % len(self.players)   # next player's turn
                self.check_end(shared_memory)
                pass

        self.end_game(pipes)
        for p in processes:
            p.join()
        shared_memory.clear()
        msg_queue.remove()
        sys.exit(0)








class Player:
    def __init__(self, id, socket):
        self.id = id
        self.socket = socket
        self.hand = {}
        self.game_over = False

    # process for receiving message from player's terminal through socket
    def recv_sock_msg(self, queue):
        while True:
            message = self.socket.recv(1024).decode()
            queue.put(message)

    def send_sock_msg(self, message):
        self.socket.send(message.encode())

    # process for receiving message from server through pipe
    def recv_pipe_msg(self, pipe, queue):
        msg_server = pipe.recv()
        while msg_server != "GAME OVER":
            queue.put(msg_server)
            msg_server = pipe.recv()
        queue.put("GAME OVER")
        result = pipe.recv()
        queue.put(result)

    def send_pipe_msg(self, pipe, message):
        pipe.send(message)

    # process for receiving message from other players through message queue
    def recv_msg_queue_msg(self, queue, msg_queue):
        while True:
            message, player = msg_queue.receive()
            msg_data = message.decode()
            if player != self.id:   # only recevie message from other players
                print(msg_data)
                queue.put("INFORMATION RECEIVED")
                queue.put(msg_data)

    def send_msg_queue_msg(self, message, msg_queue):
        message_byte = message.encode()
        msg_queue.send(message_byte, type = self.id)


    # process for each player
    def play(self, game_lock, shared_memory, msg_queue_key, pipe):
        self.send_sock_msg("Welcome to Hanabi!\n")
        self.send_sock_msg(f"Your id is {self.id}\n")
        # create a queue to receive message from server through pipe, another queue to receiver message from player's terminal through socket
        msg_queue = sysv_ipc.MessageQueue(msg_queue_key)
        queue_msg_queue = mp.Queue(maxsize=1)
        queue_sock = mp.Queue(maxsize=1)
        queue_pipe = mp.Queue(maxsize=1)
        sock_recv_proc = mp.Process(target=self.recv_sock_msg, args=(queue_sock,))
        sock_recv_proc.start()
        pipe_recv_proc = mp.Process(target=self.recv_pipe_msg, args=(pipe, queue_pipe,))
        pipe_recv_proc.start()
        msg_queue_recv_proc = mp.Process(target=self.recv_msg_queue_msg, args=(queue_msg_queue, msg_queue))
        msg_queue_recv_proc.start()


        while not self.game_over:
          # if message queue has information to be received, receive it firstly, then play the game 
            while not queue_msg_queue.empty() :
              msg_queue_notice = queue_msg_queue.get()
              if msg_queue_notice == "INFORMATION RECEIVED":
                 msg = queue_msg_queue.get()
                 self.send_sock_msg(msg) 

            msg_server = queue_pipe.get()
            while msg_server != "Your turn" and msg_server != "GAME OVER":
                print(msg_server)
                msg_server = queue_pipe.get()

            if msg_server == "Your turn":
                print("Your turn")
              # when it is player's turn
                game_lock.acquire()
                while True:
                    self.send_sock_msg(msg_server)
                    tokens_left = shared_memory["tokens"]
                    fuses_left = shared_memory["fuses"]
                    self.send_sock_msg(f"You have {tokens_left} tokens left and {fuses_left} fuses left\n")
                    action = queue_sock.get()
                    # play card  
                    if action == "PLAY CARD":
                        self.play_card(shared_memory,pipe, queue_sock, msg_queue)
                    # give information      
                    elif action == "GIVE INFORMATION":
                        self.give_information(shared_memory, pipe, queue_sock, msg_queue)
                    # end turn
                    game_lock.release()
                    break
                self.send_pipe_msg(pipe, "END TURN")
                self.send_sock_msg("Your turn ended\n")

            elif msg_server == "GAME OVER":
                self.game_over = True

        print("GAME OVER")
        self.send_sock_msg("GAME OVER")
        result = queue_pipe.get()
        self.send_sock_msg(result)
        sock_recv_proc.join()
        pipe_recv_proc.join()
        msg_queue_recv_proc.terminate()
        queue_msg_queue.close()
        queue_sock.close()
        queue_pipe.close()
        pipe.close()



    # the action of playing a card
    def play_card(self, shared_memory, pipe, queue_sock,msg_queue):
        self.send_pipe_msg(pipe, "PLAY CARD")

        playable = False
        suits_string = ""
        for suit,number in shared_memory["suits"].items():
          suits_string += f"{suit}:{number} "
        self.send_sock_msg(suits_string)
        index = [i for i, card in self.hand.items() if card is not None]
        self.send_sock_msg(f"{index}")

        card_played_index = int(queue_sock.get())
        card_played = self.hand[card_played_index]
        # check if card is playable
        if card_played.number == shared_memory["suits"][card_played.color] + 1:
            shared_memory["suits"][card_played.color] += 1
            card_played.played = True
            playable = True
        # if not, discard the card
        else: 
            shared_memory["fuses"] -= 1
            shared_memory["discards"].append(card_played)     

        if playable:
            self.send_sock_msg(f"You successfully played card {card_played.color} {card_played.number}\n")
            msg_queue_message = f"{self.id} played card {card_played.color} {card_played.number}\n"
            # if card is 5, add a token
            if card_played.number == 5:
                shared_memory["tokens"] += 1

        # if card is not playable, lose a fuse       
        else:
            self.send_sock_msg(f"You displayed card {card_played.color} {card_played.number}\n")
            msg_queue_message = f"{self.id} displayed card {card_played.color} {card_played.number}\n"

        try:
            self.send_msg_queue_msg(msg_queue_message, msg_queue)
        except:
            print("error in sending message to message queue")
            pass
        self.hand[card_played_index] = None
        self.draw_card(shared_memory)

    # the action of giving information to another player
    def give_information(self, shared_memory, pipe, queue_sock, msg_queue):
        self.send_pipe_msg(pipe, "GIVE INFORMATION")
        players_id = shared_memory["players_id"]
        other_players_id = [i for i in players_id if i != self.id]
        self.send_sock_msg(f"{other_players_id}")

        player_choice = int(queue_sock.get())
        cards_player = shared_memory["player_cards"][player_choice]
        cards_player_send = {index: [card.color,card.number] for index, card in cards_player.items()} 
        # new dict of cards for sending by socket
        self.send_sock_msg(f"{cards_player_send}")      

        type_info = queue_sock.get()
        # choose to give color information
        if type_info == "1":
            print("give color information")

            color_choice = queue_sock.get()
            print(color_choice)
            cards_position = ",".join(str(i) for i, card in cards_player.items() if card.color == color_choice)
            print(cards_position)
            try:
                self.send_msg_queue_msg(f"{player_choice} has {color_choice} cards at position {cards_position}", msg_queue)
            except:
                print("error in sending message to message queue")
                pass

        # choose to give number information   
        elif type_info == "2":
            number_choice = int(queue_sock.get())
            cards_position = ",".join(str(i) for i, card in cards_player.items() if card.number == number_choice)
            print(cards_position)
            try:
                self.send_msg_queue_msg(f"{player_choice} has cards of {number_choice} at position {cards_position}", msg_queue)
            except:
                print("error in sending message to message queue")
                pass

        # lose a token after giving information
        shared_memory["tokens"] -= 1



    # draw a card from shared memory[cards] to player's hand
    def draw_card(self, shared_memory):
        if len(shared_memory["cards"]) > 0:
            for index,card in self.hand.items():
                    if card is None:
                      self.hand[index] = shared_memory["cards"].pop()
                    break
            self.send_sock_msg("You successfully draw a card\n")
        else:
            self.send_sock_msg("No more cards in the deck\n")





class Card:
    def __init__(self, color, number):
        self.color = color
        self.number = number
        self.played = False





'''
class CountingMessageQueue:
    def __init__(self, key, num_processes):
        self.queue = sysv_ipc.MessageQueue(key, sysv_ipc.IPC_CREAT)
        self.lock = mp.Lock()
        self.counter = 1
        self.num_processes = num_processes

    def send(self, message, type):
        self.queue.send(struct.pack('!I', type) + message)

    def receive(self):
        with self.lock:
            message, _ = self.queue.receive()
            msg_type = struct.unpack('!I', message[:4])[0]
            msg_data = message[4:]
            self.counter += 1
            return msg_type, msg_data

    def delete_if_all_received(self):
        with self.lock:
            if self.counter >= self.num_processes:
                self.queue.remove()
                print("Message deleted.")
'''

