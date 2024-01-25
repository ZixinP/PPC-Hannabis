import multiprocessing as mp
import threading
import sysv_ipc

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
        return
        
    def draw_card(self,player,shared_memory):
        if len(shared_memory["cards"]) > 0:
            player.hand.append(shared_memory["cards"].pop())   
            return
        else:
            self.feedback(player.id, "No more cards in the deck\n")
            return
        
    # send message to player      
    def feedback(self, id, message):
        for p in self.players:
            if p.id == id:
                p.socket.send(message.encode())    
        return
    
    def update_game(self, shared_memory):
        shared_memory["tokens"] = self.tokens
        shared_memory["fuses"] = self.fuses
        shared_memory["discards"] = self.discards
        shared_memory["suits"] = self.suits
        shared_memory["cards"] = self.cards
        return
    
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
            self.update_game    
             
        if playable:
            self.feedback(self.players[self.turn].id, "You successfully played a " + card.color + " " + str(card.number)+"\n")
            # if card is 5, add a token
            if card.number == 5:
                self.tokens += 1
                for p in self.player:
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
            shared_memory["players"] = list_players_id
            
            processes = [mp.Process(target=p.play, args=(self, shared_memory)) for p in self.players]
            for p in processes:
                p.start()
    
    # start the game        
    def start_game(self):
        
        self.distribute_cards()
        while not self.signal:
            with self.self_lock:
                self.feedback(self.players[self.turn].id, "Your turn\n")
                action = self.players[self.turn].socket.recv(1024).decode()
                
                if action[0] == "PLAY CARD":
                    self.play_card(self.players[self.turn].hand[int(action[1])])
                elif action[0] == "GIVE INFORMATION":
                    self.give_info(self.players[self.turn], action[1])
                   
                self.update_player(self.players[self.turn])
                self.feedback(self.players[self.turn].id, "Your turn is over\n")         
                self.turn = (self.turn + 1) % len(self.players)   # next player's turn
                self.check_end()
        
        self.end_game()
        






class Player:
    def __init__(self, id, socket):
        self.id = id
        self.socket = socket
        self.hand = []
        
    def play(self, game, shared_memory, msg_queue):
        
        message = self.socket.recv(1024).decode()
        while message != "Your turn\n":
            print(message)

        game.self_lock.acquire()
        while True:
            choice = input("Enter the number of your choice: 1 for play card, 2 for give information\n")
            try :
                choice = int(choice)
                break
            except:
                print("Enter a valid number")
            
            if choice == 1:
                card_choice = input("Enter the number of the card you want to play\n")
                while True:
                    try:
                        card_choice = int(card_choice)
                        break
                    except:
                        print("Enter a valid number for card that you want to play")
                card_played = self.hand[card_choice]
                card_played.played = True
                self.hand.pop(card_choice)  # remove the card from hand
                self.socket.send(f"PLAY CARD".encode())
                self.socket.send(f"PLAY CARD {card_choice}".encode())
                    
            elif choice == 2:
                self.socket.send("GIVE INFORMATION".encode())
                other_players =[p for p in shared_memory["players"] if p != self.id]
                player_choice = input(f"Enter the number of the player among {other_players} you want to give information to \n")
                while True:
                    try:
                        player_choice = int(player_choice)
                        break
                    except:
                        print("Enter a valid number for player that you want to give information to")
                
                message_out = 
                
                
                print(cards_info)
                info_choice = input(f"Enter the type of the information you want to give, 1 for color, 2 for number\n")
                while True:
                    try:
                        info_choice = int(info_choice)
                        break
                    except:
                        print("Enter a valid number for type of information")
                    
                    
                    
                    
                    
                
                


                
            
            
            
            
            
            
            
            
            
            
            
        game.self_lock.release()
            
    
    
    
    
    
    
    
    
    
    
    
    
    
class card:
    def __init__(self, color, number):
        self.color = color
        self.number = number
        self.played = False
