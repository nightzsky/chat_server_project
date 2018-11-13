# -*- coding: utf-8 -*-
"""
Created on Tue Nov  6 11:10:23 2018

@author: Nightzsky
"""

from socket import *
from collections import deque 
import threading   
import time   
import json
import os

ip_address = "127.0.0.1"
port = 65432
server_socket = socket(AF_INET,SOCK_STREAM)
server_socket.bind((ip_address,port))

chatroom = {}

checktransfer = threading.Condition()

class ClientThread():
    def __init__(self,username,client,chatroom):
        self.username = username
        self.chatroom = chatroom
        self.client = client
        self.received_message = deque()
        self.outstanding_segments = set()
        self.msg_state = "normal"
        
        self.seq_no = 0 #unacknowledged packet sequence number
        self.next_seq_no = 1 #the next sequence number / = the ack no received from the client
        self.ack_no = 1 # the sequence number that expected from the received packet
        self.MSS = 1400

        
    #construct ack packet
    def construct_ack_packet(self,ack_no):
        msg_format = "01"+str("%06d"%self.next_seq_no)+str("%06d"%ack_no)
        packet = bytes(msg_format,"utf8")
        return packet
    
    #construct format for the packet
    def construct_broadcast_packet(self,ackf,finf,message):
        msg_format = self.username+":"+message
        packet = str(finf)+str(ackf)+str("%06d"%self.next_seq_no)+str("%06d"%self.ack_no)+msg_format
        packet = bytes(packet,"utf8")
        return packet
    
    #construct packet that is to be sent to the user himself/herself
    def construct_packet_without_username(self,ackf,finf,message):
        msg_format = str(finf)+str(ackf)+str("%06d"%self.next_seq_no)+str("%06d"%self.ack_no)+message
        packet = bytes(msg_format,"utf8")
        return packet
    
    #Broadcast the message to all other users except the sender
    def broadcast(self,message):
        for user in chatroom[self.chatroom].onlineMembers:
            if user != self.username:
                packet = self.construct_broadcast_packet(0,0,message)
                chatroom[self.chatroom].clients[user].sendall(packet)
                
    #dissect the packet received to get the seq no and ack no and message
    def dissect_packet(self,packet):
        finf = int(packet[0])
        ackf = int(packet[1])
        recv_seq_no = int(packet[2:8])
        recv_ack_no = int(packet[8:14])
        message = packet[14:]
        return finf,ackf,recv_seq_no,recv_ack_no,message
                
    #A thread will be created to listen to message from the client
    def receive(self):
        while True:
            packet = self.client.recv(1024).decode("utf-8")
            print(packet)
            finf,ackf,recv_seq_no,recv_ack_no,message = self.dissect_packet(packet)
            
            #new message received
            if ackf == 0:
                print("Received message from %s"%self.username + " : " + message)
                #if the sequence number of the packet received is what we expected
                if recv_seq_no == self.ack_no:
                    status = "new"
                    self.ack_no += self.MSS
                        
                    #remove future packets
                    while self.ack_no in self.outstanding_segments:
                        self.ack_no += self.MSS

                #if the sequence number of the packet received is greater than what we expected, add the future packet to outstanding segment, and send a ack for the packet that we are looking for and start the timer.
                elif recv_seq_no > self.ack_no:
                    status = "future"
                    self.outstanding_segments.add(packet)

                #if the packet is what we received before, ignore it 
                else:
                    status = "duplicate"
                        
                #send acknowledgement to all packets received
                ack_packet = self.construct_ack_packet(self.ack_no)
                self.client.sendall(ack_packet)
                    
                #handle system commands
                if message == "/onlineMembers":
                    new_message = "/onlineMembers"+json.dumps({"onlineMembers":chatroom[self.chatroom].onlineMembers})
                    packet = self.construct_packet_without_username(0,0,new_message)
                    self.client.sendall(packet)
                    self.next_seq_no += self.MSS
                
                elif message == "/viewMembers":
                    new_message = "/allMembers"+json.dumps({"allMembers":chatroom[self.chatroom].allMembers})
                    packet = self.construct_packet_without_username(0,0,new_message)
                    self.client.sendall(packet)
                    self.next_seq_no += self.MSS
                
                elif message == "/viewRequests":
                    if self.isAdmin():
                        new_message = "/viewRequests"+json.dumps({"joinRequests":chatroom[self.chatroom].joinRequests})
                        packet = self.construct_packet_without_username(0,0,new_message)
                        self.client.sendall(packet)
                        self.next_seq_no +=self.MSS
                    else:
                        new_message = "/viewRequests"+json.dumps({"joinRequests":"You're not an admin!"})
                        packet = self.construct_packet_without_username(0,0,new_message)
                        self.client.sendall(packet)
                        self.next_seq_no += self.MSS
                    
                elif message == "/whoIsAdmin":
                    new_message = "/whoIsAdmin"+chatroom[self.chatroom].admin
                    packet = self.construct_packet_without_username(0,0,new_message)
                    self.client.sendall(packet)
                    self.next_seq_no += self.MSS
                    
                elif message == "/transferFile":
                    print("Prepare for file transfer")
                    packet = self.construct_packet_without_username(0,0,"/transferFile filename")
                    self.client.sendall(packet)
                    
                    #received ack
                    self.client.recv(1024).decode("utf-8")
                    self.client.recv(1024).decode("utf-8")
                    filename = self.client.recv(1024).decode("utf-8")[14:]
                    packet = self.construct_packet_without_username(0,0,"/transferFile sendFile")
                    self.client.sendall(packet)
                    
                    remaining = int.from_bytes(self.client.recv(4),'big')
                    
                    f = open("temp "+filename,'wb')
                    while remaining:
                        data = self.client.recv(min(remaining,4096))
                        remaining -= len(data)
                        f.write(data)
                    f.close()
                    print("File:",filename,"from:",self.username,"has been received in chatroom:",self.chatroom)
                    
                    for user in chatroom[self.chatroom].onlineMembers:
                        if user != self.username:
                            packet = self.construct_packet_without_username(0,0,"/receivingfile")
                            userClient = chatroom[self.chatroom].clients[user]
                            userClient.sendall(packet)
                            userClient.sendall(bytes(filename,"utf-8"))
                            with open("temp "+ filename,'rb') as f:
                                data = f.read()
                                dataLen = len(data)
                                image_byte = dataLen.to_bytes(4,"big")
                                userClient.sendall(image_byte)
                                userClient.sendall(data)
                                
                elif message == "/kickMember":
                    if (self.isAdmin()):
                        packet = self.construct_packet_without_username(0,0,"/kickMember")
                        self.client.sendall(packet)
                        #receive ack
                        self.client.recv(1024)
                        self.client.recv(1024)
                        member = self.client.recv(1024).decode("utf-8")[14:]
                        if member in chatroom[self.chatroom].allMembers:
                            chatroom[self.chatroom].remove(member)
                            if member in chatroom[self.chatroom].onlineMembers:
                                chatroom[self.chatroom].remove_online_members(member)
                                #inform the member that he/she is being kicked
                                packet = self.construct_packet_without_username(0,0,"/kicked")
                                chatroom[self.chatroom].clients[member].sendall(packet)
                                del chatroom[self.chatroom].clients[member]
                        else:
                            packet = self.construct_packet_without_username(0,0,"/kickMemberMember does not exist!")
                            self.client.sendall(packet)
                            
                        print(chatroom)
                        

                    else:
                        packet = self.construct_packet_without_username(0,0,"/kickMemberYou're not an admin!")
                        self.client.sendall(packet)
                        
                elif message == "/acceptMember":
                    if (self.isAdmin()):
                        packet = self.construct_packet_without_username(0,0,"/acceptMember")
                        self.client.sendall(packet)
                        self.client.recv(1024)
                        self.client.recv(1024)
                        member = self.client.recv(1024).decode("utf-8")[14:]
                        print(member)
                        if member in chatroom[self.chatroom].joinRequests:
                            packet = self.construct_packet_without_username(0,0,"/accepted")
                            chatroom[self.chatroom].waitClients[member].sendall(packet)
                        chatroom[self.chatroom].remove_join_request(member)
                        chatroom[self.chatroom].add_new_client(member,chatroom[self.chatroom].waitClients[member])
                        chatroom[self.chatroom].remove_wait_client(member)
                    else:
                        packet = self.construct_packet_without_username(0,0,"/acceptMemberYou are not an admin")
                        self.client.sendall(packet)
                        
                        

                else:
                    print("Received from %s"%self.username+":"+message)
                    self.broadcast(message)
                    self.next_seq_no += self.MSS
                    self.received_message.append(message)
            
    #check if the client is admin
    def isAdmin(self):
        if self.username == chatroom[self.chatroom].admin:
            return True
        else:
            return False
    
            
    def start(self):
        threading.Thread(target=self.receive).start()
        
        
seq_no = 0
next_seq_no = 1
ack_no = 1

class ChatServer:
    def __init__(self):
        self.chatroom_list = []
        self.chatroom = "SUTD"
        self.admin = None
        self.joinRequests = []
        self.onlineMembers =[]
        self.allMembers = []
        self.offlineMessages = {}
        self.waitClients = {}
        self.clients = {}
        
    #construct broadca
    def construct_broadcast_packet(self,ackf,finf,message):
        new_message = self.username+":"+message
        packet = str(finf)+str(ackf)+"%06d"%next_seq_no+"%06d"%ack_no+new_message
        packet = bytes(packet,"utf8")
        return packet
    
    def construct_packet_without_username(self,ackf,finf,message):
        msg_format = str(finf)+str(ackf)+"%06d"%next_seq_no+"%06d"%ack_no+message
        packet = bytes(msg_format,"utf8")
        return packet
    
    def construct_packet_with_username(self,ackf,finf,message):
        new_message = self.username + " : " + message
        msg_format = str(finf)+str(ackf)+"%06d"%next_seq_no+"%06d"%ack_no+ new_message
        packet = bytes(msg_format, "utf8")
        return packet
    
    def broadcast(self,username):
        packet = self.construct_broadcast_packet(0,0,"%s has joined the chatroom!"%username)
        for user in self.onlineMembers:
            if user != username:
                self.clients[user].sendall(packet)
    
    def handle_connection(self):
        server_socket.listen(3)
        
        while True:
            client,client_address = server_socket.accept()
            packet = self.construct_packet_without_username(0,0,"What is your username?")
            client.sendall(packet)
            username = client.recv(1024).decode("utf-8")
            print("Received: %s from %s:%s"%(username,client_address[0],client_address[1]))
            packet = self.construct_packet_without_username(0,0,"What is the name of the chatroom?")
            client.sendall(packet)

            chatroom_name = client.recv(1024).decode("utf-8")
            print("Received: %s from %s:%s"%(chatroom_name,client_address[0],client_address[1]))
            if chatroom_name not in self.chatroom_list:
                new_chatroom = ChatRoom(chatroom_name,username,client)
                chatroom[chatroom_name] = new_chatroom
                self.chatroom_list.append(chatroom_name)
                client.sendall(bytes("New chatroom %s is created!"%chatroom_name,"utf8"))
                clientThread = ClientThread(username,client,chatroom_name)
                clientThread.start()
                
            else:
                exist_chatroom = chatroom[chatroom_name]
                exist_chatroom.add_join_request(username)
                exist_chatroom.add_wait_client(username,client)
                for user in exist_chatroom.onlineMembers:
                    packet = self.construct_packet_without_username(0,0,"%s has requested to join the chat!"%username)
                    exist_chatroom.clients[user].sendall(packet)
                client.sendall(bytes("Please wait for admin's approval","utf8"))
                clientThread = ClientThread(username,client,chatroom_name)
                clientThread.start()
                
                    
#                
#
#            if chatroom_name == self.chatroom:
#                client.sendall(bytes("%s has joined the chatroom!"%username,"utf8"))
#                self.add_new_client(username,client)
#                if self.admin is None:
#                    self.admin = username
#                #update the global variable
#                chatroom[self.chatroom] = {}
#                chatroom[self.chatroom]["admin"] = self.admin
#                chatroom[self.chatroom]["joinRequests"] = self.joinRequests
#                chatroom[self.chatroom]["onlineMembers"] = self.onlineMembers
#                chatroom[self.chatroom]["allMembers"] = self.allMembers
#                chatroom[self.chatroom]["offlineMessages"] = self.offlineMessages
#                chatroom[self.chatroom]["waitClients"] = self.waitClients
#                chatroom[self.chatroom]["clients"]=self.clients
#
#                time.sleep(2)
#                clientThread = ClientThread(username,client,self.chatroom)
#                clientThread.start()
                
#            else:
#                client.sendall(bytes("Chatroom does not exist!","utf8"))
                

    #add the new client connection to the server
    def add_new_client(self,username,client):
        self.onlineMembers.append(username)
        self.allMembers.append(username)
        self.clients[username] = client
    
    #remove the client connection from the server
    def logout(self,username):
        self.onlineMembers.remove(username)
        del self.clients[username]

    #get client connection
    def get_client(self,username):
        return self.clients[username]
            
    def start(self):
        self.handle_connection()
         
class ChatRoom:
    def __init__(self,chatroom,admin,client):
        self.chatroom = chatroom
        self.admin = admin
        self.joinRequests = []
        self.onlineMembers =[admin]
        self.allMembers = [admin]
        self.offlineMessages = {}
        self.waitClients = {}
        self.clients = {}
        self.clients[admin] = client
        
    def add_new_client(self,username,client):
        self.clients[username] = client
        if username not in self.allMembers:
            self.allMembers.append(username)
        self.onlineMembers.append(username)
    
    def logout(self,username):
        self.onlineMembers.remove(username)
        
    def add_join_request(self,username):
        self.joinRequests.append(username)
    
    def remove_join_request(self,username):
        self.joinRequests.remove(username)
        
    def remove_online_members(self,username):
        self.onlineMembers.remove(username)
    
    def kick_members(self,username):
        self.remove_online_members(username)
        self.addMembers.remove(username)
        
    def add_wait_client(self,username,client):
        self.waitClients[username] = client
    
    def remove_wait_client(self,username):
        del self.waitClients[username]
        
    def remove_member(self,username):
        self.allMembers.remove(username)
    
        
    
        
        
        
            
chatRoom = ChatServer().start()

        
        
        
            
            
            
        
    
    