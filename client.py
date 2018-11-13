import socket
import threading
import pickle
import time
from collections import deque
import json
import os
#import learnvideocapture

stage = {}

Lock = threading.Condition()


class Sender():
    def __init__(self,socket):
        self.socket = socket
        self.seq_no = 0 #the first unacknowldged packet
        self.next_seq = 1 #the sequence number for the next packet
        self.ack = 1 #the latest acknowledgement number received
        
        self.received_packets = deque() #queue for received packets
        self.outstanding_segments = set() #for the packets after the unacknowledged packet
        self.history_message = [] #sent packets stored here, for retransmitting the packet
        
        self.MSS = 1400 #the maximum size that each packet can send
        self.cwnd = 1 * self.MSS #cwnd*mss = bytes
        self.ssthresh = 64 * 1024 #64kb
        self.dupack = 0
        self.state = "slow_start"
        
        self.retransmission_timer = None
        self.retransmit_timeout = 2
        
        self.log_cache = None
       
        self.seq_log, self.ack_log = [], []
    
        self.msg_state = "normal"
        
    #construct packet with message, ack_flag, fin_flag
    def construct_packet(self,message,ack_flag,fin_flag):
        msg_format = str(fin_flag)+str(ack_flag)+str("%06d"%self.next_seq) + str("%06d"%self.ack) + message
        packet = bytes(msg_format,"utf8")
        return packet
    
    #constrcut acknowledgemnet packet
    def construct_ack_packet(self,ack_no):
        msg_format = "01"+str("%06d"%self.next_seq) +str("%06d"%ack_no)
        packet = bytes(msg_format, "utf8")
        return packet
    
    #disect the packet received into fin_flag,ack_flag,recv_seq_no,recv_ack_no and message
    def dissect_packet(self,packet):
        fin_flag = int(packet[0])
        ack_flag = int(packet[1])
        recv_seq_no = int(packet[2:8])
        recv_ack_no = int(packet[8:14])
        message = packet[14:]
        
        return fin_flag,ack_flag,recv_seq_no,recv_ack_no,message
    
    #obtain the loss packet for retransmission
    def get_resend_packet(self,seq_no):
        for i in range(len(self.history_message)):
            fin_flag,ack_flag,packet_seq_no,ack_no,message = self.dissect_packet(self.history_message[i])
            if packet_seq_no == seq_no:
                return self.history_message[i]
            
    #get the current allowed sending buffer
    def get_current_sending_rate(self):
        return self.cwnd
    
    #This function handles all the user input/sending function
    def send(self):
        while True:
            if self.msg_state == "transfer_file":
                continue
            if self.msg_state == "kick_member":
                continue
            if self.msg_state == "kicked":
                continue
            if self.msg_state == "accept_member":
                continue
            message = input()
            if message == "view":
                print("CWND: "+str(self.cwnd))
                print("Latest Ack Received: "+str(self.ack))
                print("First unacknowledged sequence number: "+str(self.seq_no))
                print("Next sequence number: "+ str(self.next_seq))
                print("Current ssthresh: " +str(self.ssthresh))
                print("Current dupack: " +str(self.dupack))
                continue
            
            if message == "/openVideo":
                
#                learnvideocapture.captureVideo()
                
                continue
            
            if message == "/congestionControl":
                self.congestionControl()
                continue
                
            #Normal message does not include finf and ackf
            packet = self.construct_packet(message,0,0)
            self.socket.sendall(packet)
                
            #after sending, update the next sequence number, add the amount of the payload
            self.next_seq += self.MSS
            #add to the sent data list
            self.history_message.append(packet)
            
            #start the timer
            if self.retransmission_timer is None:
                self.retransmission_timer = time.time()
    
    #resend the lost packet during time loss or triple duplicate
    def resend(self,recv_ack_no):
        packet = self.get_resend_packet(recv_ack_no)
        self.retransmission_timer = time.time() #restart timer
        self.socket.sendall(packet)
        print("Resent packet")
    
    #send acknowledgement packet
    def send_ack(self,ack_no):
        packet = self.construct_ack_packet(ack_no)
        self.socket.sendall(packet)
        print("Sent ack")
       
    #send fin packet to end connection
    def send_fin(self):
        packet = self.construct_packet("/logout",0,1)
        self.socket.sendall(packet)
        print("Sent fin")
        
    #timeout function, it is to be run be a thread
    def timeout(self):
        while True:
            if self.retransmission_timer is None:
                continue
            elif self.retransmission_timer + self.retransmit_timeout < time.time():
                self.resend(self.ack)
                self.state = "slow_start"
                self.ssthresh = self.cwnd/2
                self.cwnd = 1 * self.MSS
                self.dupack = 0
                self.retransmission_timer = None
    
    #listen to all messages received and add to self.received_packet
    def receive(self):
        while True:
            packet = self.socket.recv(1024).decode("utf8")
            fin_flag,ack_flag,recv_seq_no,recv_ack_no,message = self.dissect_packet(packet)
            
            #data packet received
            if ack_flag == 0:
                #if the received sequence number is what we expect
                if recv_seq_no == self.ack:
                    status = "new"
                    self.ack += self.MSS
                    #if the later packet is already inside the outstanding_segments, remove them
                    while self.ack in self.outstanding_segments:
                        self.outstanding_segments.remove(self.ack)
                        self.ack += self.MSS
                
                #add the future packet to the outstanding segments since it is not the segment we are expecting
                elif recv_seq_no > self.ack:
                    status = "future"
                    self.outstanding_segments.add(recv_seq_no)
                #duplicate packet(already received) being sent, ignore the packet
                else:
                    status = "duplicate"  
                #send acknowledgement to these packets (self.ack is the next sequence number for the server)
                self.send_ack(self.ack)
                
            #if ack received, acknowledgement sent from the server
            elif ack_flag == 1:
                print("Received ack no: %s"%str(recv_ack_no))
                #ack is received to acknowledge new data,restart the retransmission timer
                
                if  recv_ack_no-1 > self.seq_no:
                    self.seq_no = recv_ack_no-1
                    self.retransmission_timer = time.time()
                    #in slow start, for every ack received, cwnd + 1 MSS
                    
                    if self.state == "slow_start":
                        self.cwnd += self.MSS
                    
                    #in congestion avoidance, for every ack received, cwnd = cwnd + 1/cwnd
                    elif self.state == "congestion_avoidance":
                        self.cwnd += self.MSS / self.cwnd
                        
                    #in fast recovery, the state enter congestion avoidance mode
                    elif self.state == "fast_recovery":
                        self.state = "congestion_avoidance"
                        self.cwnd = self.ssthresh
                    self.dupack=0
                
                #if recv_ack_no  <= self.seq, means duplicate
                else:
                    #duplicate ack
                    self.dupack += 1
                    
                    #if triple duplicate, enter fast_recovery stage, and the ssthresh is saved as current cwnd/2 and cwnd will be equal to the new ssthresh
                    
                    if self.dupack == 3:
                        print("TRIPLE DUPLICATE!!")
                        self.state = "fast_recovery"
                        self.ssthresh = self.cwnd/2
                        self.cwnd = self.ssthresh+3*self.MSS
                        self.resend(recv_ack_no)
                        
                    elif self.state == "fast_recovery":
                        self.cwnd += self.MSS
                        
            #fin received from server
            elif fin_flag == 1:
                if self.state == "fin_sent":
                    return "tear_down"
            
            #process message received
            if message == "":
                continue
            
            elif "/onlineMembers" in message:
                new_message = message.replace(message[:14],"")
                data = json.loads(new_message)["onlineMembers"]
                print("Online Users: ")
                for element in data:
                    print(element)
                    
            elif "/allMembers" in message:
                print("testing")
                print(message)
                new_message = message.replace(message[:11],"")
                data = json.loads(new_message)["allMembers"]
                print("All Chatroom Users: ")
                for element in data:
                    print(element)
                    
            elif "/viewRequests" in message:
                new_message = message.replace(message[:13],"")
                data = json.loads(new_message)["joinRequests"]
                if len(data)==0:
                    print("No join requests")
                else:
                    if "admin" in data:
                        print(data)
                    else:
                        print("Join requests:")
                        for element in data:    
                            print(element)
                    
            elif "/whoIsAdmin" in message:
                new_message = message.replace(message[:11],"")
                print(new_message)
                
            elif "/kickMember" in message:
                self.msg_state = "kick_member"
                new_message = message.replace(message[:11],"")
                if "admin" in new_message:
                    print(new_message)
                else:
                    print("Press enter and then key in the member to be kicked")
                    username = input("Please enter the username")
                    packet = self.construct_packet(username,0,0)
                    self.socket.sendall(packet)
                self.msg_state = "normal"
                
            elif message == "/kicked":
                print("You are kicked from the group! Press any key to quit")
                self.msg_state = "kicked"
                break
                              
            elif message == "/acceptMember":
                self.msg_state = "accept_member"
                new_message = message.replace(message[:13],"")
                if "admin" in new_message:
                    print(new_message[13:])
                else:
                    print("Press enter and then key in the member to be accepted")
                    username = input("Please enter the username")
                    packet = self.construct_packet(username,0,0)
                    self.socket.sendall(packet)
                self.msg_state = "normal"
                
            elif "/transferFile" in message:
                self.msg_state = "transfer_file"
                print("Press enter and then key in your filename")
                filename = input("Please enter the filename")
                packet = self.construct_packet(filename,0,0)
                self.socket.sendall(packet)
                self.socket.recv(1024).decode("utf-8")
                print("Uploading to server...")
                with open(filename,'rb') as f:
                    data = f.read()
                    dataLen = len(data)
                    image_byte = dataLen.to_bytes(4,'big')
                    self.socket.sendall(image_byte)
                    self.socket.sendall(data)
                    
                print("Uploaded successfully!")
                self.msg_state = "normal"
                
            elif message == "/receivingfile":
                print("Downloading chatroom file...")
                filename = self.socket.recv(1024).decode("utf-8")

                remaining = int.from_bytes(self.socket.recv(4),"big")
                new_filename = "received "+filename
                f = open(new_filename, 'wb')
                while remaining:
                    data = self.socket.recv(min(remaining,4096))    
                    remaining -= len(data)
                    f.write(data)
                f.close()
                print("File ", filename, " received")
#            elif message == "/logOut":
                
            else:
                print(message)
    
    def congestionControl(self):
        for i in range(10):
            time.sleep(2)
            dump_load = '*'*(500)
            packet = self.construct_packet(dump_load,0,0)
            self.history_message.append(packet)
            if i != 2:
                self.socket.sendall(packet)
                self.next_seq += self.MSS
            else:
                self.next_seq += self.MSS
            print(str(i)+ " Transmission Round\nCurrent sending rate: %s"%str(self.cwnd)+ "\nCurrent congestion state: %s"%self.state+"\n\n")
        


    
    def start(self):
        threading.Thread(target=self.send).start()
        threading.Thread(target=self.receive).start()
        
def waitForAcceptance(serverSocket):
    while not stage['accept']:
        message = serverSocket.recv(1024).decode("utf-8")[14:]
        print(message)
        if "/accepted" in message:
            new_message = message[9:]
            print("Welcome to %s"%new_message)
            print("Chatroom Commands:\n/viewMembers -> See all chatroom members\n/onlineMembers -> See all online chatroom members\n/viewRequests -> See all the pending requests (Only admin) \n/acceptMember -> Accept a new request (Only admin) \n/kickMember -> Kick a member out of the group (Only admin) \n /whoIsAdmin -> Check who is the admin of this chat \n/transferFile -> Transfer files to other members\n/openVideo -> Open the webcam for recording\n/congestionControl -> to view how cwnd changes when packet loss.\nJust type whenever you want to send any messages!")         
            client = Sender(serverSocket)
            client.start()
            stage['accept'] = True
        elif "/rejected" in message:
            print("Sorry, you are being rejected! Press any key to quit!")
            break
            
        
    


portnumber = 65432
ip = "127.0.0.1"
serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
serverSocket.connect((ip,portnumber))
message = serverSocket.recv(1024).decode("utf-8")
print(message[14:])
username = input("Please enter your username:")
serverSocket.sendall(bytes(username,"utf8"))

response = serverSocket.recv(1024).decode("utf-8")
print(response[14:])  
chatroom = input("Please enter the chatroom name:")
serverSocket.sendall(bytes(chatroom,"utf8"))
response = serverSocket.recv(1024).decode("utf-8")

print("Please wait...")
time.sleep(2)
print(response)

if "created" in response:
    print(response)
    stage['accept'] = True
    print("Chatroom Commands:\n/viewMembers -> See all chatroom members\n/onlineMembers -> See all online chatroom members\n/viewRequests -> See all the pending requests (Only admin) \n/acceptMember -> Accept a new request (Only admin) \n/kickMember -> Kick a member out of the group (Only admin) \n /whoIsAdmin -> Check who is the admin of this chat \n/transferFile -> Transfer files to other members\n/openVideo -> Open the webcam for recording\n/congestionControl -> to view how cwnd changes when packet loss.\nJust type whenever you want to send any messages!")      
    client = Sender(serverSocket)
    client.start()
    
else:
    stage['accept'] = False
    print("Please wait for admin acceptance.")
    listenAcceptance = threading.Thread(target=waitForAcceptance,args=(serverSocket,))
    listenAcceptance.start()

#if "does not" in response:
#    serverSocket.close()
#else:
#    print("Chatroom Commands:\n/viewMembers -> See all chatroom members\n/onlineMembers -> See all online chatroom members\n/transferFile -> Transfer files to other members\n/openVideo -> Open the webcam for recording\n/congestionControl -> to view how cwnd changes when packet loss.\nJust type whenever you want to send any messages!")              
#    client = Sender(serverSocket)
#    client.start()
