import multiprocessing as mp
from queue import Queue
import sysv_ipc
import struct
import signal

color = ['red', 'blue', 'green', 'yellow', 'white'] 
key = 111

class Game:   
    def __init__(self, players, color,key):
        self.cards = self.init_cards(color)
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
            desk_cards.append(card(c,1))
            for i in range (1,4):
                desk_cards.append(card(c,i))
                desk_cards.append(card(c,i))
            desk_cards.append(card(c,5))
            self.suits[c] = 0   # initialize the number of cards played for each suit
        return desk_cards
            
    def distribute_cards(self,shared_memory):
        for p in self.players:
            for i in range(0,5):
                p.hand[i] = shared_memory["cards"].pop()
                '''
                try:
                    p.hand[i] = shared_memory["cards"].pop()
                except:
                    self.feedback(p.id, " Error in distributing cards from shared memory\n")   
                    p.hand[i] = self.cards.pop()  
                '''
        
        
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
            for s in shared_memory["suits"]:
                if s.value !=5:
                    FLAG = False
            if FLAG:
                self.signal = True
                self.win = True
                return
    
    
    # notify players the game ends
    def end_game(self,pipes):
        for player_id, pipe in pipes:
            pipe.send("GAME OVER")
            if self.win:
                pipe.send(f"Congratulations! You win the game")
            else:
                pipe.send(f"Sorry, you lose the game")

        
    # create a shared memory for all players and start all players' processes
    def set_up_players(self):  
        with mp.Manager() as manager:
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
            shared_memory["player_cards"] = {[p.id]:p.hand for p in self.players}
            msg_queue = sysv_ipc.MessageQueue(self.queue_id, sysv_ipc.IPC_CREAT)
            pipes = []
            processes = []
            for p in self.players:
                server_pipe, player_pipe = mp.Pipe()
                pipes.append([p.id, server_pipe])
                p_process = mp.Process(target=p.play, args=(self, shared_memory, msg_queue, player_pipe))
                processes.append(p_process)
           
            for process in processes:
                process.start()
        
        return shared_memory, processes, pipes
            
            
    # start the game        
    def start_game(self):
        self.distribute_cards() 
        shared_memory, processes, pipes = self.set_up_players()

        while not self.signal:
            with self.self_lock:
                pipe_turn = next(pipe[1] for pipe in pipes if pipe[0] == self.turn)   # find the pipe of the player whose turn it is
                if pipe_turn:
                    pipe_turn.send("Your turn")
                else:
                    print("Error in finding pipe")      
                
                action_player = pipe_turn.recv()
                print(action_player)
                
                end_turn = pipe_turn.recv()
                self.update_game(shared_memory)    # update the game status from shared memory to local memory
                self.turn = (self.turn + 1) % len(self.players)   # next player's turn
                self.check_end()
                pass
        self.end_game()
        for p in processes:
            p.join()
        msg_queue.remove()
        sys.exit()
        
        






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
        self.game_over = True
        
    def send_pipe_msg(self, pipe, message):
        pipe.send(message)
        
    # process for receiving message from other players through message queue
    def recv_msg_queue_msg(self, msg_queue):
        while True:
            message, _ = self.queue.receive()
            msg_type = struct.unpack('!I', message[:4])[0]
            msg_data = message[4:]
            if msg_type != self.id:
                print(msg_data)
                self.send_sock_msg("INFORMATION RECEIVED")
                self.send_sock_msg(msg_data)
    
    def send_msg_queue_msg(self, msg_queue, message):
        msg_queue.send(struct.pack('!I', self.id) + message)
            
    
    # process for each player
    def play(self, game, shared_memory, msg_queue, pipe):
        self.send_sock_msg("Welcome to Hanabi!\n")
        
        # create a queue to receive message from server through pipe, another queue to receiver message from player's terminal through socket
        queue_sock = Queue()
        queue_pipe = Queue()
        sock_recv_proc = mp.Process(target=self.recv_sock_msg, args=(queue_sock,))
        sock_recv_proc.start()
        pipe_recv_proc = mp.Process(target=self.recv_pipe_msg, args=(msg_queue, queue_pipe,))
        pipe_recv_proc.start()
        msg_queue_recv_proc = mp.Process(target=self.recv_msg_queue_msg, args=(msg_queue))
        msg_queue_recv_proc.start()
        
        
        while not self.game_over:
            msg_server = queue_pipe.get()
            while msg_server != "Your turn" and msg_server != "RECEIVE INFORMATION":
                print(msg_server)
                msg_server = queue_pipe.get()
            
            if msg_server == "Your turn":
                # when it is player's turn
                game.self_lock.acquire()
                while True:
                    self.send_sock_msg(msg_server)
                    tokens_left = shared_memory["tokens"]
                    fuses_left = shared_memory["fuses"]
                    self.send_sock_msg(f"You have {tokens_left} tokens left and {fuses_left} fuses left\n")
                    action = queue_sock.get()
                    # play card  
                    if choice == 1:
                        self.play_card(self, shared_memory,game, msg_queue,pipe)
                    # give information      
                    elif choice == 2:
                        self.give_information(self, shared_memory, game, msg_queue, pipe)
                    # end turn
                    game.self_lock.release()
                    
                self.send_pipe_msg(pipe, "END TURN")
        
        self.send_sock_msg("GAME OVER")
        result = queue_pipe.get()
        self.send_sock_msg(result)
        sock_recv_proc.join()
        pipe_recv_proc.join()
        msg_queue_recv_proc.join()
        sys.exit()

         
    
    # the action of playing a card
    def play_card(self, shared_memory, game, msg_queue, pipe):
        self.send_pipe_msg(pipe, "PLAY CARD")
        
        playable = False
        for suit in shared_memory["suits"]:
            suits_string += f"{suit}: {shared_memory['suits'][suit]}"
        self.send_sock_msg(suits_string)
        index = [i for i, card in self.hand.items() if card != None]
        self.send_sock_msg(f"{index}")
        
        card_played_index = queue_sock.get()
        card_played = self.hand[card_played_index]
        # check if card is playable
        if card_played.number == shared_memory["suits"][card.color] + 1:
            shared_memory["suits"][card.color] += 1
            card.played = True
            playable = True
        # if not, discard the card
        else: 
            shared_memory["fuses"] -= 1
            shared_memory["discards"].append(card)      
             
        if playable:
            self.send_sock_msg(f"You successfully played card {card.color} {str(card.number)}\n")
            msg_queue_message = f"{self.id} played card {card.color} {str(card.number)}\n"
            # if card is 5, add a token
            if card.number == 5:
                shared_memory["tokens"] += 1
        
        # if card is not playable, lose a fuse       
        elif not playable:
            self.send_sock_msg(f"You displayed card {card.color} {str(card.number)}\n")
            msg_queue_message = f"{self.id} displayed card {card.color} {str(card.number)}\n"
        
        self.send_msg_queue_msg(msg_queue, msg_queue_message)
        self.hand[card_played_index] = None
        self.draw_card(shared_memory)
    
    # the action of giving information to another player
    def give_information(self, shared_memory, game, msg_queue, pipe):
        self.send_pipe_msg(pipe, "GIVE INFORMATION")
        players_id = shared_memory["players_id"]
        self.send_sock_msg(f"{players_id}\n")
        
        player_choice = queue_sock.get()
        cards_player = shared_memory["player_cards"][player_choice]
        self.send_sock_msg(f"{cards_player}\n")         
        
        type_info = queue_sock.get()
        # choose to give color information
        if type_info == 1:
            color_choice = queue_sock.get()
            cards_position = [i for i, card in cards_player.items() if card.color == color_choice]
            self.send_msg_queue_msg(msg_queue, f"{player_choice} has {color_choice} cards at position {cards_position}")
        # choose to give number information   
        elif type_info == 2:
            number_choice = queue_sock.get()
            cards_position = [i for i, card in cards_player.items() if card.number == number_choice]
            self.send_msg_queue_msg(msg_queue, f"{player_choice} has {number_choice} cards at position {cards_position}")
        
        shared_memory["tokens"] -= 1
            
            
        
    
    def draw_card(self, shared_memory):
        if len(shared_memory["cards"]) > 0:
            for index in self.hand.keys():
                if self.hand[index] == None:
                    self.hand[index] = shared_memory["cards"].pop()
                    break
            self.send_sock_msg(f"You successfully draw a card\n")
        else:
            self.send_sock_msg("No more cards in the deck\n")
            
    
    


class card:
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

