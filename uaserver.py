#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Clase (y programa principal) para un Programa User Agent Server."""

import socketserver
import sys
import os
import socket
import time
from uaclient import hora_actual
from uaclient import fichero_log
from uaclient import cvlc
from uaclient import rtp
from threading import Thread


class ProxyHandler(socketserver.DatagramRequestHandler):
    """Proxy server class."""

    RTP = {'IP': '', 'PORT': 0}  # IP y Puerto del UACLIENT (INVITE)

    def handle(self):
        u"""Implementación de los Metodos INVITE, ACK y BYE."""
        # Escribe dirección y puerto del cliente (de tupla client_address)
        IP_CLIENTE = str(self.client_address[0])
        PUERTO_CLIENTE = int(self.client_address[1])
        print("La direccion y puerto del cliente es: " +
              str(self.client_address))
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            linea_cliente = self.rfile.read()
            metodo_cliente = linea_cliente.decode('utf-8').split(' ')[0]
            # Incluimos lo recibido en fichero log
            texto = " ".join(linea_cliente.decode('utf-8').split("\r\n"))
            if texto != "":
                fichero_log(PATH_LOG, "received", IP_CLIENTE, PUERTO_CLIENTE,
                            texto)
            # Si no hay más líneas salimos del bucle infinito
            if not linea_cliente:
                break

            print("El cliente nos manda: \r\n" + linea_cliente.decode('utf-8'))

            if metodo_cliente not in metodos_posibles:
                respuesta = ("SIP/2.0 405 Method Not Allowed" + '\r\n')
                self.wfile.write(bytes(respuesta, 'utf-8') + b'\r\n')

            elif metodo_cliente == "INVITE":
                self.RTP["IP"] = linea_cliente.decode('utf-8').split(' ')[6]
                self.RTP["PORT"] = linea_cliente.decode('utf-8').split(' ')[7]

                if Thread(target=rtp, args=(self.RTP["IP"], self.RTP["PORT"],
                          PATH_AUDIO,)).isAlive():
                    # Recibimos INVITE mientras envío RTP
                    respuesta = "SIP/2.0 480 Temporarily Unavailable\r\n"
                else:
                    # Mandamos código respuesta
                    respuesta = ("SIP/2.0 100 Trying" + '\r\n\r\n' +
                                 "SIP/2.0 180 Ringing" + '\r\n\r\n' +
                                 "SIP/2.0 200 OK" + '\r\n')
                    respuesta += "Content-Type: application/sdp\r\n\r\n"
                    respuesta += "v=0\r\n" + "o=" + USERNAME + " " + IP
                    respuesta += "\r\ns=misesion" + "\r\n" + "t=0" + "\r\n"
                    respuesta += "m=audio " + PUERTO_RTP + " RTP"

                print("Codigo respuesta a INVITE:  \r\n", respuesta)
                self.wfile.write(bytes(respuesta, 'utf-8') + b'\r\n')
                data = respuesta.split('\r\n')
                texto = " ".join(data)
                fichero_log(PATH_LOG, "sent_to", IP_CLIENTE, PUERTO_CLIENTE,
                            texto)

            elif metodo_cliente == 'ACK':
                # Mandamos RTP al UACLIENT
                # VLC con Hilos
                hilo1 = Thread(target=cvlc, args=(self.RTP["IP"],
                               self.RTP["PORT"],))
                hilo2 = Thread(target=rtp, args=(self.RTP["IP"],
                               self.RTP["PORT"], PATH_AUDIO,))
                hilo1.start()
                time.sleep(0.2)
                hilo2.start()

            elif metodo_cliente == 'BYE':
                respuesta = "SIP/2.0 200 OK\r\n"
                print("Codigo respuesta a BYE: \r\n", respuesta)
                self.wfile.write(bytes(respuesta, 'utf-8') + b'\r\n')
                data = respuesta.split('\r\n')
                texto = " ".join(data)
                fichero_log(PATH_LOG, "sent_to", IP_CLIENTE, PUERTO_CLIENTE,
                            texto)
                fichero_log(PATH_LOG, "finishing", IP, PUERTO, "")
                # Paramos envío RTP y VLC
                os.system('killall mp32rtp 2> /dev/null')
                os.system('killall vlc 2> /dev/null')

            else:
                respuesta = ("SIP/2.0 400 Bad Request" + '\r\n')
                self.wfile.write(bytes(respuesta, 'utf-8') + b'\r\n')
                data = respuesta.split('\r\n')
                texto = " ".join(data)
                fichero_log(PATH_LOG, "sent_to", IP_CLIENTE, PUERTO_CLIENTE,
                            texto)

if __name__ == "__main__":
    try:
        CONFIGURACION = sys.argv[1]
    except IndexError:
        sys.exit('Usage: python uaserver.py config')

    print("Listening...")

    metodos_posibles = ['INVITE', 'ACK', 'BYE']
    # Abrimos fichero xml para coger informacion
    fichero = open(CONFIGURACION, 'r')
    linea = fichero.readlines()
    fichero.close()

    # Conseguimos nombre de usuario y contraseña (linea 3-xml)
    linea_account = linea[2].split(">")
    account = linea_account[0].split("=")[1]
    USERNAME = account.split(" ")[0][1:-1]
    passw = linea_account[0].split("=")[2]
    PASSWORD = passw.split(" ")[0][1:-2]
    # IP
    linea_uaserver = linea[3].split(">")
    uaserver = linea_uaserver[0].split("=")[1]
    IP = uaserver.split(" ")[0][1:-1]
    if not IP:
        IP = "127.0.0.1"
    # PUERTO DEL UASERVER
    uaserver_puerto = linea_uaserver[0].split("=")[2]
    PUERTO = uaserver_puerto.split(" ")[0][1:-2]
    # PUERTO RTP
    linea_rtpaudio = linea[4].split(">")
    rtpaudio = linea_rtpaudio[0].split("=")[1]
    PUERTO_RTP = rtpaudio.split(" ")[0][1:-2]
    # IP y PUERTO DEL PROXY
    linea_regproxy = linea[5].split(">")
    regproxy = linea_regproxy[0].split("=")[1]
    IP_PROXY = regproxy.split(" ")[0][1:-1]
    regproxy_puerto = linea_regproxy[0].split("=")[2]
    PUERTO_PROXY = regproxy_puerto.split(" ")[0][1:-2]
    # Ubicacion Path log
    linea_log = linea[6].split(">")
    log = linea_log[0].split("=")[1]
    PATH_LOG = log.split(" ")[0][1:-2]
    # Ubicacion Path Audio
    linea_audio = linea[7].split(">")
    audio = linea_audio[0].split("=")[1]
    PATH_AUDIO = audio.split(" ")[0][1:-2]

    # Creamos el socket, lo configuramos y lo atamos a un servidor/puerto
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.connect((IP_PROXY, int(PUERTO_PROXY)))

    serv = socketserver.UDPServer(((IP, int(PUERTO))), ProxyHandler)
    serv.serve_forever()
