import multiprocessing as mp
# import threading
import sysv_ipc
# import struct
import signal

class Game:
    color = ['red', 'blue', 'green', 'yellow', 'white'] 
    key = 111
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
        self.msg_queue = sysv_ipc.MessageQueue(key, sysv_ipc.IPC_CREAT)
    
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
            
    def distribute_cards(self):
        for p in self.players:
            for i in range(0,5):
                p.hand.append(self.draw_card())

        
    def draw_card(self,player,shared_memory):
        if len(shared_memory["cards"]) > 0:
            player.hand.append(shared_memory["cards"].pop())   
 
        else:
            self.feedback(player.id, "No more cards in the deck\n")
        
    # send message to player      
    def feedback(self, id, message):
        for p in self.players:
            if p.id == id:
                p.socket.send(message.encode())    

    
    def update_game(self, shared_memory):
        shared_memory["tokens"] = self.tokens
        shared_memory["fuses"] = self.fuses
        shared_memory["discards"] = self.discards
        shared_memory["suits"] = self.suits
        shared_memory["cards"] = self.cards

    
    #check if game is over
    def check_end(self, shared_memory):
        FLAG = False
        if shared_memory["fuses"] == 0:
            self.signal = True
            self.win = False
            return
        for s in shared_memory["suits"]:
            if s.value == 5:
                FLAG = True
        if FLAG:
            self.signal = True
            self.win = True
        return
    
    # notify players the game ends
    def end_game(self):
        for p in self.players:
            self.feedback(p.id, "Game over\n")
            if self.win:
                self.feedback(p.id, "You win\n")
            else:
                self.feedback(p.id, "You lose\n")
    
    # the action of playing a card
    def play_card(self, card, shared_memory):
        
        playable = False
        # check if card is playable
        if card.number == shared_memory["suits"][card.color] + 1:
            self.suits[card.color] += 1
            card.played = True
            playable = True
        # if not, discard the card
        else: 
            shared_memory["fuses"] -= 1
            shared_memory["discards"].append(card)      
            self.update_game(shared_memory) 
             
        if playable:
            self.feedback(self.players[self.turn].id, "You successfully played a " + card.color + " " + str(card.number)+"\n")
            # if card is 5, add a token
            if card.number == 5:
                self.tokens += 1
                for p in self.players:
                    self.feedback(p.id, "Suit %s completed\n" % card.color)
                    self.feedback(p.id, "You received a token\n") 
            self.update_game(shared_memory)
                
        # if card is not playable, lose a fuse       
        else:
            self.feedback(self.players[self.turn].id, f"You misplayed card {card.color} {str(card.number)}\n")
            self.feedback(self.players[self.turn].id, "You lost a fuse\n")
            for p in self.player:
                self.feedback(p.id, f"only {self.fuses} fuses left\n")
        

    def set_up_players(self):  
        with mp.Manager() as manager:
            # create a shared memory for all players, in form of dictionary
            shared_memory = manager.dict()
            shared_memory["tokens"] = self.tokens
            shared_memory["fuses"] = self.fuses
            shared_memory["discards"] = self.discards
            shared_memory["suits"] = self.suits
            shared_memory["cards"] = self.cards
            # collect all players' id
            list_players_id = [p.id for p in self.players]
            shared_memory["players_id"] = list_players_id
            
            processes = [mp.Process(target=p.play, args=(self, shared_memory,self.msg_queue)) for p in self.players]
            for p in processes:
                p.start()
            return shared_memory, processes
    
    
    
    # start the game        
    def start_game(self):
        self.distribute_cards() 
        shared_memory, processes = self.set_up_players()
         
        signal.signal(signal.SIGINT, self.signal_handler)
        try:
            while not self.signal:
                with self.self_lock:
                    self.feedback(self.players[self.turn].id, "Your turn\n")
                    action = self.players[self.turn].socket.recv(1024).decode()
                    
                    if action == "PLAY CARD":
                        card = self.players[self.turn].socket.recv(1024).decode()
                        self.play_card(card, shared_memory)
                    elif action == "GIVE INFORMATION":
                        player_choice = self.players[self.turn].socket.recv(1024).decode()
                        player_card = self.players[player_choice].hand
                        self.players[self.turn].socket.send(player_card)
                        self.feedback(self.players[player_choice].id, "RECEIVE INFORMATION")
                    
                    self.update_game(shared_memory)
                    self.feedback(self.players[self.turn].id, "Your turn is over\n")         
                    self.turn = (self.turn + 1) % len(self.players)   # next player's turn
                    self.check_end()
    
            self.end_game()
            for p in processes:
                p.join()
        
        except KeyboardInterrupt:
            print("Game interrupted")
            signal_handler(siganl.SIGINT, None)
        
        return
    
    def signal_handler(self, sig, frame):
        self.signal = True
        return





class Player:
    def __init__(self, id, socket):
        self.id = id
        self.socket = socket
        self.hand = []
        
    def play(self, game, shared_memory, msg_queue):
        message = self.socket.recv(1024).decode()
        while message != "GAME OVER":   
            while message != "Your turn\n":
                while message != "RECEIVE INFORMATION":
                    print(message)
                
                # when reveive notification from server to receive information from other player
                info_card = msg_queue.receive(type = 1)
                print(info_card)
            
            # when it is player's turn
            game.self_lock.acquire()
            while True:
                choice = input("Enter the number of your choice: 1 for play card, 2 for give information\n")
                try :
                    choice = int(choice)
                    break
                except:
                    print("Enter a valid number")
                
                # play card  
                if choice == 1:
                    # tell server to play card
                    self.socket.send(f"PLAY CARD".encode())
                    
                    card_choice = input("Enter the number of the card you want to play\n")
                    while True:
                        try:
                            card_choice = int(card_choice)
                            break
                        except:
                            print("Enter a valid number for card that you want to play")
                    card_played = self.hand[card_choice]
                    card_played.played = True
                    self.hand.pop(card_choice)   # remove the card from hand
                    self.socket.send(f"PLAY CARD {card_choice}".encode())
                
                # give information      
                elif choice == 2:
                    # tell server to give information
                    self.socket.send("GIVE INFORMATION".encode())  
                    other_players =[p for p in shared_memory["players_id"] if p != self.id]
                    
                    player_choice = input(f"Enter the number of the player among {other_players} you want to give information to \n")
                    while True:
                        try:
                            player_choice = int(player_choice)
                            break
                        except:
                            print("Enter a valid number for player that you want to give information to")
                    
                    # tell server which player to give information to
                    self.socket.send(f"GIVE INFORMATION {player_choice}".encode())
                    player_card = self.socket.recv(1024).decode()
                    print(player_card)    # print all the cards of the player
                    info_choice = input(f"Enter the type of the information you want to give, 1 for color, 2 for number\n")
                    while True:
                        try:
                            info_choice = int(info_choice)
                            break
                        except:
                            print("Enter a valid number for type of information")
                    
                    # choose to give color information
                    if info_choice == 1:
                        color = input("Enter the color you want to give information about\n")
                        while True:
                            if color in (card.color for card in player_card):
                                break
                            else:
                                print("Enter a valid color")
                        cards_position = [i for i, card in enumerate(player_card) if card.color == color]
                        # tell player the position of the cards with the color
                        msg_queue.send(f"Position of {color} cards are {cards_position}", type = 1)  
                    
                    # choose to give number information
                    elif info_choice == 2:
                        number = input("Enter the number you want to give information about\n")
                        while True:
                            if number in (card.number for card in player_card):
                                break
                            else:
                                print("Enter a valid number")
                        cards_position = [i for i, card in enumerate(player_card) if card.number == number]
                        msg_queue.send(f"Position of {number} cards are {cards_position}", type = 1)
                
            game.self_lock.release()
        
        self.socket.close()   
    
    
    
    
    

class card:
    def __init__(self, color, number):
        self.color = color
        self.number = number
        self.played = False