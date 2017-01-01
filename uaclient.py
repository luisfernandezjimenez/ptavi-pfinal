#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Programa User Agent Client que abre un socket a un servidor."""

import sys
import socket
import hashlib
import os
import time
from threading import Thread


def hora_actual():
    """Se define el Tiempo Actual."""
    tiempo_actual = time.time()
    return time.strftime("%Y%m%d%H%M%S", time.gmtime(tiempo_actual))


def fichero_log(fichero, evento, ip, puerto, texto):
    """Se define el Fichero_log."""
    fichero = open(fichero, 'a')
    hora = fichero.write(hora_actual())

    if evento == "sent_to":
        fichero.write(" Sent to " + ip + ":" + str(puerto) + ":  " +
                      texto + "\r\n")
    elif evento == "received":
        fichero.write(" Received from " + ip + ":" + str(puerto) + ":  " +
                      texto + "\r\n")
    elif evento == "error":
        fichero.write(texto + '\r\n')
    elif evento == "starting":
        fichero.write(" Starting... \r\n")
    elif evento == "finishing":
        fichero.write(" Finishing. \r\n")

    fichero.close()


def cvlc(IP_RTP, PUERTO_RTP):
    """Se definde cvlc."""
    aEjecutarVLC = 'cvlc rtp://@' + IP_RTP + ':'
    aEjecutarVLC += PUERTO_RTP + ' 2> /dev/null &'
    print("Vamos a ejecutar", aEjecutarVLC)
    os.system(aEjecutarVLC)


def rtp(IP_RTP, PUERTO_RTP, PATH_AUDIO):
    """Se define rtp."""
    aEjecutar = ('./mp32rtp -i ' + IP_RTP + ' -p ' +
                 PUERTO_RTP + ' < ' +
                 PATH_AUDIO.split('./')[1])
    print("Vamos a ejecutar", aEjecutar)
    os.system(aEjecutar)
    print('Envío de audio finalizado.')

if __name__ == "__main__":
    try:
        CONFIGURACION = sys.argv[1]
        METODO = sys.argv[2].upper()
        OPCION = sys.argv[3]
    except IndexError:
        sys.exit('Usage: python uaclient.py config method option')

    # Abrimos fichero xml para coger informacion
    fichero_xml = open(CONFIGURACION, 'r')
    linea = fichero_xml.readlines()
    fichero_xml.close()

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

    # METODOS
    if METODO == 'REGISTER':
        # Comenzamos a escribir fichero log --> Starting
        fichero_log(PATH_LOG, "starting", IP, PUERTO, "")
        LINEA = METODO + ' sip:' + USERNAME + ':' + PUERTO
        LINEA += ' SIP/2.0\r\n' + "Expires: " + OPCION + "\r\n"
    elif METODO == 'INVITE':
        # Añadimos cabeceras
        LINEA = METODO + " sip:" + OPCION + " SIP/2.0\r\n"
        LINEA += "Content-Type: application/sdp\r\n\r\n"
        LINEA += "v=0\r\n" + "o=" + USERNAME + " " + IP + "\r\n"
        LINEA += "s=misesion" + "\r\n" + "t=0" + "\r\n"
        LINEA += "m=audio " + PUERTO_RTP + " RTP" + "\r\n"
    elif METODO == 'BYE':
        # BYE sip:receptor SIP/2.0
        LINEA = METODO + " sip:" + OPCION + " SIP/2.0\r\n"
    else:
        LINEA = METODO

    # Enviamos la petición
    print("Enviando: \r\n" + LINEA)
    my_socket.send(bytes(LINEA, 'utf-8') + b'\r\n')
    # Lo escribimos en archivo log
    data = LINEA.split('\r\n')
    texto = " ".join(data)
    fichero_log(PATH_LOG, "sent_to", IP_PROXY, PUERTO_PROXY, texto)

    # Recibimos respuesta
    try:
        data = my_socket.recv(1024)
        print("Recibido: \r\n", data.decode('utf-8'))
    except socket.error:
        texto = "Error: No server listening at " + IP_PROXY
        texto += " port " + PUERTO_PROXY
        fichero_log(PATH_LOG, "error", IP, PUERTO, texto)
        sys.exit(fichero_log)

    # Estudiamos respuesta recibida y la incluimos en el fichero log
    data = data.decode('utf-8').split("\r\n")
    texto = " ".join(data)
    fichero_log(PATH_LOG, "received", IP_PROXY, PUERTO_PROXY, texto)
    hilos = {'hilo1': Thread(), 'hilo2': Thread()}

    if data[0] == "SIP/2.0 401 Unauthorized":
        # Añadimos cabecera autenticación (FUNCION HASH)
        m = hashlib.md5()
        nonce = data[1].split("=")[-1]
        nonce = nonce.split('"')[1]
        m.update(bytes(PASSWORD, 'utf-8'))
        m.update(bytes(nonce, 'utf-8'))
        LINEA += "Authorization: Digest response=" + '"' + m.hexdigest()
        LINEA += '"' + "\r\n"
        print("Enviando: \r\n" + LINEA)
        my_socket.send(bytes(LINEA, 'utf-8') + b'\r\n')
        data = LINEA.split('\r\n')
        texto = " ".join(data)
        fichero_log(PATH_LOG, "sent_to", IP_PROXY, PUERTO_PROXY, texto)
        data = my_socket.recv(1024)
        print("Recibido: \r\n", data.decode('utf-8'))
        data = data.decode('utf-8').split('\r\n')
        texto = " ".join(data)
        fichero_log(PATH_LOG, "received", IP_PROXY, PUERTO_PROXY, texto)
    elif data[0] == "SIP/2.0 100 Trying":
        # Metodo de asentimiento. ACK sip:receptor SIP/2.0
        METODO = 'ACK'
        LINEA = METODO + ' sip:' + OPCION + ' SIP/2.0\r\n'
        print("Enviando: \r\n" + LINEA)
        my_socket.send(bytes(LINEA, 'utf-8') + b'\r\n')
        lista = LINEA.split('\r\n')
        texto = " ".join(lista)
        fichero_log(PATH_LOG, "sent_to", IP_PROXY, PUERTO_PROXY, texto)

        # Envio RTP con Hilos
        # aEjecutar es un string con lo que se ha de ejecutar en la shell
        IP_RTP = data[9].split(' ')[-1]
        PUERTO_RTP = data[12].split(' ')[-2]
        # VLC con Hilos
        hilos['hilo1'] = Thread(target=cvlc, args=(IP_RTP, PUERTO_RTP,))
        hilos['hilo2'] = Thread(target=rtp, args=(IP_RTP, PUERTO_RTP,
                                PATH_AUDIO,))
        hilos['hilo1'].start()
        time.sleep(0.2)
        hilos['hilo2'].start()
    elif data[0] == "SIP/2.0 200 OK":
        # Paramos envío RTP y VLC
        os.system('killall mp32rtp 2> /dev/null')
        os.system('killall vlc 2> /dev/null')
        # Terminamos de escribir en el fichero log --> Finishing
        fichero_log(PATH_LOG, "finishing", IP, PUERTO, "")
        print("Terminando socket...")
        # Cerramos todo
        my_socket.close()
        print("Fin.")
