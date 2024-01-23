import threading

class Game:
    color = ['red', 'blue', 'green', 'yellow', 'white'] 
    def __init__(self, players, color):
        self.cards = self.init_cards(color)
        self.players = players
        self.suits={}
        self.round = 0
        self.turn = 0
        self.self_lock = threading.Lock()
        self.tokens = len(players) +3
        self.fuses = 3
        self.discards = []
        self.signal = False
        self.win= False
       
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
        return desk_cards
            
    def distribute_cards(self):
        for p in self.players:
            for i in range(0,5):
                p.hand.append(self.draw_card())
            self.update_player(p)
        
    def draw_card(self):
        return self.cards.pop()
    
    def play_card(self, card):
        
        playable = False
        # check if card is playable
        if card.number == self.suits[card.color] + 1:
            self.suits[card.color] += 1
            card.played = True
            playable = True
        # if not, discard the card
        else: 
            self.fuses -= 1
            self.discards.append(card)           
            
        if playable:
            self.feedback(self.players[self.turn].id, "You successfully played a " + card.color + " " + str(card.number)+"\n")
            # if card is 5, add a token
            if card.number == 5:
                self.tokens += 1
                for p in self.player:
                    self.feedback(p.id, "Suit %s completed\n" % card.color)
                    self.feedback(p.id, "You received a token\n")      
        # if card is not playable, lose a fuse       
        else:
            self.feedback(self.players[self.turn].id, f"You played a {card.color} {str(card.number)}\n")
            self.feedback(self.players[self.turn].id, "You lost a fuse\n")
            for p in self.player:
                self.feedback(p.id, f"{self.fuses} fuses left\n")
        
        card_drew = self.draw_card()
        if card_drew == None:
            self.feedback(self.players[self.turn].id, "You have no more cards to draw\n")
        else:
            self.players[self.turn].hand.append(card_drew)
            self.feedback(self.players[self.turn].id, f"You drew a {card_drew.color} {str(card_drew.number)}\n")
    
    # send message to player      
    def feedback(self, id, message):
        for p in self.players:
            if p.id == id:
                p.socket.send(message.encode())    
        return
    
    # update player's hand
    def update_player(self, player):
        self.feedback(player.id, "Your hand: \n")
        for c in player.hand:
            self.feedback(player.id, f"{c.color} {str(c.number)}\n")
        self.feedback(player.id, "\n")
        return
    
    #check if game is over
    def check_end(self):
        if self.fuses == 0:
            self.signal = True
            self.win = False
            return
        for s in self.suits:
            if self.suits[s] == 5:
                self.signal = True
                self.win = True
                return
        return
    
    # notify players the game ends
    def end_game(self):
        for p in self.players:
            self.feedback(p.id, "Game over\n")
            if self.win:
                self.feedback(p.id, "You win\n")
            else:
                self.feedback(p.id, "You lose\n")
    
    # start the game        
    def start_game(self):
        self.distribute_cards()
        player_thread = []
        # start a thread for each player
        for player in self.players:
            player_thread.append(threading.Thread(target=player.play, args=(self,)))
            player_thread[-1].start()
        
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
        
    def play(self, game):
        
        message = self.socket.recv(1024).decode()
        while True:
            game.self_lock.acquire()
            if message == "Your turn\n":
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
                    self.socket.send(f"PLAY CARD {card_choice} {card_played.color} {card_played.number}".encode())
                    
                elif choice == 2:
                    self.socket.send("GIVE INFORMATION".encode())
                    players = self.socket.recv(1024).decode()
                    player_choice = input(f"Enter the number of the player among {players} you want to give information to \n")
                    while True:
                        try:
                            player_choice = int(player_choice)
                            break
                        except:
                            print("Enter a valid number for player that you want to give information to")
                    
                    self.socket.send(player_choice.encode())
                    cards_info = self.socket.recv(1024).decode()
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
