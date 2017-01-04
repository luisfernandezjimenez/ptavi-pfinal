#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Programa Proxy."""

import sys
import socketserver
import socket
import json
import random
import hashlib
import csv
import time
from uaclient import hora_actual
from uaclient import fichero_log


class ProxyHandler(socketserver.DatagramRequestHandler):
    """Proxy server class."""

    # Diccionario con los Usuarios que estan registrados
    usuarios_registrados = {}

    def register2json(self):
        """Se registra al cliente en un fichero json."""
        with open('registered.json', 'w') as file:
            json.dump(self.usuarios_registrados, file,
                      sort_keys=True, indent=4)

    def json2registered(self):
        """Se mira si hay un fichero registered.json."""
        try:
            with open('registered.json', 'r') as fichero:
                fichero_json = json.loads(fichero.read())
                self.usuarios_registrados = fichero_json
        except:
            pass

    def handle(self):
        u"""Implementación de los Metodos INVITE, ACK y BYE."""
        # Escribe dirección y puerto del cliente (de tupla client_address)
        self.json2registered()
        IP_CLIENTE = str(self.client_address[0])
        PUERTO_CLIENTE = self.client_address[1]
        while 1:
            # Leyendo línea a línea lo que nos envía el cliente
            linea = self.rfile.read()
            metodo_cliente = linea.decode('utf-8').split(' ')[0]
            linea_troceada = linea.decode('utf-8').split(' ')
            cabecera_proxy = 'Via: SIP/2.0/UDP ' + IP_SERVER + ':'
            cabecera_proxy += PUERTO_SERVER + ';rport;branch=z9hG4bK776asdhds'
            # Si no hay más líneas salimos del bucle infinito
            if not linea:
                break

            print("El cliente nos manda: \r\n" + linea.decode('utf-8'))
            data = linea.decode('utf-8').split("\r\n")
            linea = linea.decode('utf-8').split('\r\n')
            # Anadimos Cabecera Proxy
            linea.insert(1, cabecera_proxy)
            linea = '\r\n'.join(linea)

            if metodo_cliente not in metodos_posibles:
                respuesta = ("SIP/2.0 405 Method Not Allowed" + '\r\n')
                print("Enviando: \r\n" + respuesta)
                self.wfile.write(bytes(respuesta, 'utf-8'))
                data = respuesta.split('\r\n')
                texto = " ".join(data)
                fichero_log(PATH_LOGSERVER, "sent_to",
                            IP_CLIENTE, PUERTO_CLIENTE, texto)

            elif metodo_cliente == "REGISTER":
                direccion_sip = linea_troceada[1].split(':')[1]
                expires = int(linea_troceada[3].split('\r\n')[0])
                puerto_cliente = int(linea_troceada[1].split(':')[-1])

                if len(linea_troceada) == 4:
                    # Enviamos: SIP/2.0 401 Unauthorized
                    texto = " ".join(data)
                    fichero_log(PATH_LOGSERVER, "received",
                                IP_CLIENTE, puerto_cliente, texto)

                    if expires > 0:
                        nonce = random.randint(0, 10**20)
                        if direccion_sip in passwords_usuarios:
                            passwords_usuarios[direccion_sip]['nonce'] = nonce
                        respuesta = ("SIP/2.0 401 Unauthorized" + "\r\n")
                        respuesta += "WWW-Authenticate: Digest nonce="
                        respuesta += '"' + str(nonce) + '"' + "\r\n"

                    elif expires == 0:
                        if direccion_sip in self.usuarios_registrados:
                            # Borramos al usuario del diccionario
                            del self.usuarios_registrados[direccion_sip]
                            print("Borramos: ", direccion_sip)
                        respuesta = "SIP/2.0 200 OK" + "\r\n"

                else:
                    # Comprobamos el response
                    response = linea_troceada[-1].split('=')[-1]
                    response = response.split('"')[1]
                    texto = " ".join(data)
                    fichero_log(PATH_LOGSERVER, "received",
                                IP_CLIENTE, puerto_cliente, texto)
                    m = hashlib.md5()
                    if direccion_sip in passwords_usuarios:
                        m.update(bytes(passwords_usuarios
                                 [direccion_sip]['password'], 'utf-8'))
                        m.update(bytes(str(passwords_usuarios
                                 [direccion_sip]['nonce']), 'utf-8'))
                    with open('passwords.json', 'w') as file:
                        json.dump(passwords_usuarios, file, sort_keys=True,
                                  indent=4)

                    if m.hexdigest() == response:
                        respuesta = "SIP/2.0 200 OK\r\n"
                        hora_actual = time.time()
                        hora_exp = hora_actual + expires
                        # Añadimos usuario al JSON
                        informacion = {}
                        informacion['Direccion'] = IP_CLIENTE
                        informacion['Puerto'] = puerto_cliente
                        informacion['Fecha de Registro'] = hora_actual
                        informacion['Fecha de Expiracion'] = hora_exp
                        self.usuarios_registrados[direccion_sip] = informacion

                    else:
                        respuesta = "SIP/2.0 401 Unauthorized\r\n"
                        respuesta += "WWW-Authenticate: nonce=" + '"'
                        respuesta += str(random.randint(0, 10**20))
                        respuesta += '"' + "\r\n\r\n"

                print("Enviando: \r\n" + respuesta)
                self.wfile.write(bytes(respuesta, 'utf-8') + b'\r\n')
                data = respuesta.split('\r\n')
                texto = " ".join(data)
                fichero_log(PATH_LOGSERVER, "sent_to",
                            IP_CLIENTE, puerto_cliente, texto)

                self.register2json()

            elif metodo_cliente == "INVITE":
                texto = " ".join(data)
                fichero_log(PATH_LOGSERVER, "received",
                            IP_CLIENTE, PUERTO_CLIENTE, texto)
                # Enviamos INVITE a su destinatorio con la Cabecera Proxy
                destinatario = linea_troceada[1].split(':')[1]
                if destinatario in self.usuarios_registrados:
                    print("Se lo mandamos a: ", destinatario)
                    IP_DEST = (self.usuarios_registrados
                               [destinatario]['Direccion'])
                    PUERTO_DEST = (self.usuarios_registrados
                                   [destinatario]['Puerto'])
                    fichero_log(PATH_LOGSERVER, "sent_to",
                                IP_DEST, PUERTO_DEST, texto)
                    # Creamos socket
                    my_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
                    my_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
                    my_socket.connect((IP_DEST, int(PUERTO_DEST)))
                    my_socket.send(bytes(linea, 'utf-8'))
                    data = my_socket.recv(1024)
                    print("Recibido:\r\n", data.decode('utf-8'))
                    data = data.decode('utf-8').split("\r\n")
                    texto = " ".join(data)
                    fichero_log(PATH_LOGSERVER, "received",
                                IP_DEST, PUERTO_DEST, texto)
                    # Reenviamos al cliente con la Cabecera Proxy
                    data.insert(5, cabecera_proxy)
                    texto = " ".join(data)
                    data = '\r\n'.join(data)
                    fichero_log(PATH_LOGSERVER, "sent_to",
                                IP_CLIENTE, PUERTO_CLIENTE, texto)
                    print("Enviando: \r\n" + data)
                    self.wfile.write(bytes(data, 'utf-8'))
                else:
                    # Usuario no registrado
                    print("Usuario No Registrado")
                    respuesta = "SIP/2.0 404 User Not Found\r\n"
                    self.wfile.write(bytes(respuesta, 'utf-8') + b'\r\n')
                    print("Enviando: \r\n" + respuesta)
                    data = respuesta.split('\r\n')
                    texto = " ".join(data)
                    fichero_log(PATH_LOGSERVER, "sent_to",
                                IP_CLIENTE, PUERTO_CLIENTE, texto)

            elif metodo_cliente == "ACK":
                texto = " ".join(data)
                fichero_log(PATH_LOGSERVER, "received",
                            IP_CLIENTE, PUERTO_CLIENTE, texto)
                destinatario = linea_troceada[1].split(':')[1]
                IP_DEST = self.usuarios_registrados[destinatario]['Direccion']
                PUERTO_DEST = self.usuarios_registrados[destinatario]['Puerto']
                print("Se lo mandamos a: ", destinatario)
                # Creamos socket (Lleva Cabecera Proxy)
                my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                my_socket.connect((IP_DEST, int(PUERTO_DEST)))
                my_socket.send(bytes(linea, 'utf-8'))
                texto = " ".join(data)
                fichero_log(PATH_LOGSERVER, "sent_to",
                            IP_DEST, PUERTO_DEST, texto)

            elif metodo_cliente == "BYE":
                texto = " ".join(data)
                fichero_log(PATH_LOGSERVER, "received",
                            IP_CLIENTE, PUERTO_CLIENTE, texto)
                destinatario = linea_troceada[1].split(':')[1]
                print("Se lo mandamos a: ", destinatario)

                if destinatario in self.usuarios_registrados:
                    IP_DEST = (self.usuarios_registrados
                               [destinatario]['Direccion'])
                    PUERTO_DEST = (self.usuarios_registrados
                                   [destinatario]['Puerto'])
                    data.insert(1, cabecera_proxy)
                    texto = " ".join(data)
                    data = '\r\n'.join(data)
                    fichero_log(PATH_LOGSERVER, "sent_to",
                                IP_DEST, PUERTO_DEST, texto)
                    # Creamos socket
                    my_socket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
                    my_socket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)
                    my_socket.connect((IP_DEST, int(PUERTO_DEST)))
                    my_socket.send(bytes(linea, 'utf-8'))
                    data = my_socket.recv(1024)
                    print('Recibimos: \r\n', data.decode('utf-8'))
                    data = data.decode('utf-8').split("\r\n")
                    texto = " ".join(data)
                    fichero_log(PATH_LOGSERVER, "received",
                                IP_DEST, PUERTO_DEST, texto)
                    # Reenviamos al cliente con la Cabecera Proxy
                    data.insert(1, cabecera_proxy)
                    texto = " ".join(data)
                    data = '\r\n'.join(data)
                    print("Enviando: \r\n" + data)
                    self.wfile.write(bytes(data, 'utf-8'))
                else:
                    # Usuario no registrado
                    respuesta = "SIP/2.0 404 User Not Found\r\n"
                    print("Enviando: \r\n" + respuesta)
                    self.wfile.write(bytes(respuesta, 'utf-8') + b'\r\n')
                    data = respuesta.split('\r\n')
                    texto = " ".join(data)

                fichero_log(PATH_LOGSERVER, "sent_to",
                            IP_CLIENTE, PUERTO_CLIENTE, texto)
                fichero_log(PATH_LOGSERVER, "finishing", IP_CLIENTE,
                            PUERTO_CLIENTE, "")
            else:
                respuesta = ("SIP/2.0 400 Bad Request" + '\r\n\r\n')
                print("Enviando: \r\n" + respuesta)
                self.wfile.write(bytes(respuesta, 'utf-8'))
                data = respuesta.split('\r\n')
                texto = " ".join(data)
                fichero_log(PATH_LOGSERVER, "sent_to",
                            IP_CLIENTE, PUERTO_CLIENTE, texto)

if __name__ == "__main__":
    """Creamos servidor eco y escuchamos."""
    try:
        CONFIGURACION = sys.argv[1]
    except IndexError:
        sys.exit("Usage: python proxy_registrar.py config")

    metodos_posibles = ['REGISTER', 'INVITE', 'ACK', 'BYE']
    # Abrimos fichero xml para coger informacion
    fichero = open(CONFIGURACION, 'r')
    linea = fichero.readlines()
    fichero.close()

    # NOMBRE, PUERTO e IP del Servidor donde escuchara
    linea_server = linea[2].split(">")
    server = linea_server[0].split("=")[1]
    NAME_SERVER = server.split(" ")[0][1:-1]
    ip = linea_server[0].split("=")[2]
    IP_SERVER = ip.split(" ")[0][1:-1]
    if not IP_SERVER:
        IP_SERVER = "127.0.0.1"
    puerto = linea_server[0].split("=")[3]
    PUERTO_SERVER = puerto.split(" ")[0][1:-2]
    # Database
    linea_database = linea[3].split(">")
    database = linea_database[0].split("=")[1]
    PATH_DATABASE = database.split(" ")[0][1:-1]
    path_password = linea_database[0].split("=")[2]
    PASSWORDS_DATABASE = path_password.split("=")[0][1:-2]
    # Fichero Log
    linea_log = linea[4].split(">")
    log = linea_log[0].split("=")[1]
    PATH_LOGSERVER = log.split(" ")[0][1:-2]

    # Coger el contenido del fichero PASSWORDS.JSON
    with open('passwords.json', 'r') as fichero:
        passwords_usuarios = {}
        fichero = json.loads(fichero.read())
        passwords_usuarios = fichero

    serv = socketserver.UDPServer((IP_SERVER, int(PUERTO_SERVER)),
                                  ProxyHandler)
    print("Server " + NAME_SERVER + " listening at port " + str(PUERTO_SERVER))
    fichero_log(PATH_LOGSERVER, "starting", IP_SERVER, PUERTO_SERVER, "")
    serv.serve_forever()
