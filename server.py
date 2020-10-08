"""
Import multiple modules that will be used in this script
"""
import random
import socket
import time
from _thread import *
import threading
from datetime import datetime
import json

########################
""" GLOBALS """
########################
# creating a lock for shared threads https://realpython.com/intro-to-python-threading/#working-with-many-threads
clients_lock = threading.Lock()
# num of connected clients
connected = 0
# a dictionary that will store our clients indexed by their (IP, PORT)
clients = {}

########################
""" METHODS """
########################


def connectionLoop(sock):
    """
    Takes care of:
      1. Updating the heartbeat of an existing client
      2. Connecting a new client
    """
    while True:
        # Listen to the next message
        data, addr = sock.recvfrom(1024)
        data = str(data)
        print(addr)
        print("Got this: " + data)
        # if addr (i.e IP,PORT) exists in clients dictionary
        if addr in clients:
            # update the heartbeat value if data dictionary has a key called 'heartbeat'
            if 'heartbeat' in data:
                clients[addr]['lastBeat'] = datetime.now()

            else:
                data = data[2:len(data) -1]
                data = json.loads(data)
                clients[addr]['position'] = {
                    "x": data["x"],
                    "y": data["y"],
                    "z": data["z"]
                }

        else:
            # if there is a key called 'connect' in data dictionary
            if 'connect' in data:
                # add a new object to the client dictionary
                clients[addr] = {}
                # update the last beat of the client object
                clients[addr]['lastBeat'] = datetime.now()
                # add a field called color
                clients[addr]['position'] = 0
                # create a message object with a command value and an array of player objects
                message = {"cmd": 0, "players": []}  # {"id":addr}}

                # create a new object
                p = {}
                # add a field called 'id' that is the string version of (IP, PORT)
                p['id'] = str(addr)

                message['players'].append(p)
                # create a new gamestate object similar to message
                GameState = {"cmd": 4, "players": []}
                # for every key of clients
                for c in clients:
                    # if the key is the same as the connected player
                    if (c == addr):
                        # change command to 3
                        message['cmd'] = 3
                    else:
                        message['cmd'] = 0

                    # create a JSON string.
                    # google what the separator function does. Why do we use it here? Its not always needed.
                    m = json.dumps(message, separators=(",", ":"))

                    # create a new player object
                    player = {}
                    # set the id to the current key
                    player['id'] = str(c)

                    # add it to the game state
                    GameState['players'].append(player)
                    # send the message object containg the new connected client to the previously connected clients
                    sock.sendto(bytes(m, 'utf8'), (c[0], c[1]))

                # send the game state to the new client
                m = json.dumps(GameState)
                sock.sendto(bytes(m, 'utf8'), addr)


def cleanClients(sock):
    """
      Takes care of:
         1. Checking if a client should be dropped
         2. Letting the clients know of a drop
    """
    while True:
        # create an array
        droppedClients = []
        # for every client in keys
        # How is this different from what we did in line 67? Try and find out.
        for c in list(clients.keys()):
            # Check if its been longer than 5 seconds since the last heartbeat
            if (datetime.now() - clients[c]['lastBeat']).total_seconds() > 5:
                print('Dropped Client: ', c)
                # for thread safety, gain the lock
                clients_lock.acquire()
                # delete the client identified by c
                del clients[c]
                # releast the lock we have
                clients_lock.release()
                # add the dropped client key to the array of dropped clients
                droppedClients.append(str(c))

        # Send a JSON object with list of dropped clients to all connected clients
        message = {"cmd": 2, "disconnectedPlayers": droppedClients}
        m = json.dumps(message, separators=(",", ":"))

        if (len(droppedClients) > 0):
            for c in clients:
                sock.sendto(bytes(m, 'utf8'), (c[0], c[1]))

        time.sleep(1)


def gameLoop(sock):
    """
      Takes care of:
         1. Assigning a random color to every client
         2. Send the state to all clients
    """

    pktID = 0  # just to identify a particular network packet while debugging
    while True:
        print("Boop")
        # create a game state object
        GameState = {"cmd": 1, "pktID": pktID, "players": []}
        clients_lock.acquire()
        #      print (clients)
        for c in clients:
            # create a player object
            player = {}

            # fill the player details
            player['id'] = str(c)
            player['position'] = clients[c]['position']

            GameState['players'].append(player)
        s = json.dumps(GameState, separators=(",", ":"))
        print(s)
        # send the gamestate json to all clients
        for c in clients:
            sock.sendto(bytes(s, 'utf8'), (c[0], c[1]))
        clients_lock.release()
        if (len(clients) > 0):
            pktID = pktID + 1
        time.sleep(1/30)


########################
""" ENTRY """
########################


def main():
    print("Running server")
    """
      Start 3 new threads
    """
    port = 12345
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', port))
    start_new_thread(gameLoop, (s, ))
    start_new_thread(connectionLoop, (s, ))
    start_new_thread(cleanClients, (s, ))
    # keep the main thread alive so the children threads stay alive
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
