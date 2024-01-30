import socket
import multiprocessing as mp




def recv_socket(server_socket, pipe):
    while True:
        message = server_socket.recv(1024).decode()
        if message != "GAME OVER":
            pipe.send(message)
            
        else:
            final_result = server_socket.recv(1024).decode()
            pipe.send(message)
            pipe.send(final_result)
            break
                  

def main():
    host = '127.0.0.1'
    port = 12345
    server_socket = (host, port)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_socket)
    print("Connected to server")

    self_action = []
    other_action = []
    par_conn, child_conn = mp.Pipe()
    recv_socket = mp.Process(target=recv_socket, args=(server_socket, child_conn))

    while True:
        message = par_conn.recv()
        if message == "Your turn":
            print("1 for play card, 2 for give information to another player\n")
            action = int(input("Please enter your action: "))
            while action != 1 and action != 2:
                action = int(input("Please enter your action: "))

            action = int(action) 
            if action == 1:
                action_notice = "PLAY CARD"
                server_socket.send(action_notice.encode())
                        
                suits = par_conn.recv()
                print(f"suits: {suits}\n")
                cards_in_hand = par_conn.recv()
                card = int(input(f"Please enter the card you want to play in {cards_in_hand}: "))
                while card not in cards_in_hand:
                    card = int(input(f"Please enter the card you want to play in {cards_in_hand}: "))
                server_socket.send(card.encode())
                        
                result = par_conn.recv()
                print(f"{result}")
                self_action.append([action_notice, card, result])
                break
                    
            elif action ==2:
                action_notice = "GIVE INFORMATION"
                server_socket.send(action_notice.encode())
                        
                players_id = par_conn.recv()
                print(f"players_id: {players_id}")
                player = int(input("Please enter the player you want to give information: "))
                while player not in players_id:
                    player = int(input("Please enter the player you want to give information: "))
                server_socket.send(player.encode())
                
                cards_recv = par_conn.recv()
                print(f"player {player} has cards: {cards_recv}")
                print("1 for give color information, 2 for give number information\n")
                info_type = int(input("Please enter the information type: "))
                while info_type != 1 and info_type != 2:
                    info_type = int(input("Please enter the information type: "))
                
                server_socket.send(info_type.encode())
                # choose to give color information       
                if info_type == 1:
                    color_choice = str(input("Please enter the color: "))
                    while color_choice not in (card.color for card in cards_recv):
                        color_choice = str(input("Please enter the color: "))
                    server_socket.send(color_choice.encode())
                    self_action.append([action_notice, player, color_choice])
                    
                # choose to give number information           
                elif info_type == 2:
                    number_choice = int(input("Please enter the number: "))
                    while number_choice not in (card.number for card in cards_recv):
                        number_choice = int(input("Please enter the number: "))
                    server_socket.send(number_choice.encode())
                    self_action.append([action_notice, player, number_choice])

        
        elif message == "INFORMATION RECEIVED":
            print("You receive information from another player\n")
            information = par_conn.recv()
            print(f"{information}")
            other_action.append(information)
            
        elif message == "GAME OVER":
            print("GAME OVER")
            final_result = par_conn.recv()
            print(f"{final_result}")
            break
        
        else:
            print(message)
            
    recv_socket.join()                                    
    client_socket.close()

if __name__ == "__main__":
    main()
