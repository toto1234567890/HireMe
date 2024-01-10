#!/usr/bin/env python
# coding:utf-8

import socket, os
import ssl

def SSL_server_context():
    # https://support.microfocus.com/kb/doc.php?id=7013103
    # How to create a self-signed PEM file: 
    # openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem   
    keyPath = os.path.join(os.path.dirname(__file__), "key.pem")
    certPath = os.path.join(os.path.dirname(__file__), "cert.pem")
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=certPath, keyfile=keyPath)
    return context

def main():
    HOST = "127.0.0.1"
    PORT = 5010

    context = SSL_server_context()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, PORT))
        sock.listen(5)
        with context.wrap_socket(sock, server_side=True) as ssock:
            conn, addr = ssock.accept()
            with conn:
                print(f"Connected by {addr}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print("Data received from '{0}': {1}".format(addr, data.decode()))
                    data = "message from Server!"
                    conn.sendall(data.encode())


#================================================================
if __name__ == "__main__":
    main()



