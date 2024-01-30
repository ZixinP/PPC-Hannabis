import socket
import multiprocessing as mp
import ast



def recv_socket(client_socket, pipe):
    while True:
        message = client_socket.recv(1024).decode()
        if message != "GAME OVER":
            pipe.send(message)

        else:
            final_result = client_socket.recv(1024).decode()
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
    recv_socket_pro = mp.Process(target=recv_socket, args=(client_socket, child_conn))
    recv_socket_pro.start()

    while True:
        message = par_conn.recv()
        if message == "Your turn":
            print("Your turn\n")
            situation = par_conn.recv()
            print(f"{situation}\n")
            print("1 for play card, 2 for give information to another player")
            action = int(input("Please enter your action: "))
            while action != 1 and action != 2:
                action = int(input("Please enter your action: "))

            if action == 1:
                action_notice = "PLAY CARD"
                print(action_notice)
                client_socket.send(action_notice.encode())

                suits = par_conn.recv()
                print(f"suits: {suits}\n")
                cards_in_hand_str = par_conn.recv()
                cards_in_hand_list = ast.literal_eval(cards_in_hand_str)
                card = int(input(f"Please enter the card you want to play in {cards_in_hand_str}: "))
                while card not in cards_in_hand_list:
                    card = int(input(f"Please enter the card you want to play in {cards_in_hand_str}: "))
                client_socket.send(str(card).encode())

                result = par_conn.recv()
                print(f"{result}")
                self_action.append([action_notice, card, result])


            elif action ==2:
                action_notice = "GIVE INFORMATION"
                client_socket.send(action_notice.encode())

                players_id_str = par_conn.recv()
                players_id_list = ast.literal_eval(players_id_str)
                print(f"other players' id: {players_id_str}")
                player = int(input("Please enter the player you want to give information:"))
                while player not in players_id_list:
                    player = int(input("Please enter the player you want to give information: "))
                client_socket.send(str(player).encode())

                cards_recv_str = par_conn.recv()
                cards_recv_dict = eval(cards_recv_str)
                print(f"cards received: {cards_recv_dict}")
                print(f"player {player} has cards: {cards_recv_str}")
                print("1 for give color information, 2 for give number information")
                info_type = int(input("Please enter the information type: "))
                while info_type != 1 and info_type != 2:
                    info_type = int(input("Please enter the information type: "))

                client_socket.send(str(info_type).encode())
                # choose to give color information       
                if info_type == 1:
                    color_choice = str(input("Please enter the color: "))
                    while not any(color_choice == card[0] for card in cards_recv_dict.values()):
                      print("Color choice not found in cards.")
                      color_choice = str(input("Enter the color: "))

                    client_socket.send(color_choice.encode())
                    self_action.append([action_notice, player, color_choice])

                # choose to give number information           
                elif info_type == 2:
                    number_choice = int(input("Please enter the number: "))
                    while not any(number_choice == card[1] for card in cards_recv_dict.values()):
                      print("Number choice not found in cards.")  
                      number_choice = int(input("Please enter the number: "))
                    client_socket.send(str(number_choice).encode())
                    self_action.append([action_notice, player, number_choice])


        elif message == "INFORMATION RECEIVED":
            print("You receive information from another player")
            information = par_conn.recv()
            print(f"{information}")
            other_action.append(information)

        elif message == "GAME OVER":
            print("GAME OVER")
            final_result = par_conn.recv()
            print(f"{final_result}")
            break

        else:
            print(f"{message}")

    recv_socket_pro.join()                                  
    client_socket.close()

if __name__ == "__main__":
    main()
