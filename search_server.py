"""
Copyright 2019, University of Freiburg,
Chair of Algorithms and Data Structures.
Author: Hannah Bast <bast@cs.uni-freiburg.de>
"""

import socket
import sys
from qgram_index import *
import time
import json


class SearchServer:
    """
    An HTTP search engein server using a qgram index.
    """

    def __init__(self, file, port):
        """ Initialize with given port. """
        self.port = port
        self.se = self.build_search_engine(file)

    def build_search_engine(self, file_name):
        """
        Build a 3-gram index from given file.
        """
        qi = QGramIndex(3)
        print("Start building the 3-gram index...")
        start = time.monotonic()
        qi.build_from_file(file_name)
        end = time.monotonic()
        print(f"Done in {(end-start):.3f} seconds...")
        return qi

    def read_request(self, connection_socket):
        """
        Read request from a client connected via the connection socket.
        """
        request_bytes = bytearray()
        num_bytes = 4096
        while 1:
            try:
                data = connection_socket.recv(num_bytes)
                request_bytes.extend(data)
            except socket.timeout:
                print("Client timeout")
                break
            # TODO: validate
            if request_bytes[-2*len(data):].find(b'\r\n\r\n') >= 0:
                break
        request = request_bytes.decode('utf-8').split('\r\n')[0]
        print("Request data from client: %s" % request,"\n")
        return request

    def answer_query(self, query, max_results=5):
        """
        Answer query with the qgram index.

        Params:
            query(str): Query string.
            max_results(int): Maximum number of returning search results.
        Returns:
            Top `max_results` results.
        """
        q = self.se.normalize(query)
        raw_results = self.se.rank_matches(self.se.find_matches(q, len(q)//4))
        results = []
        for i in range(min(max_results, len(raw_results))):
            results.append(self.se.entities[raw_results[i][0]])
        return results
#            print(f'{i+1}. '+self.se.entities[results[i][0]]['name']+'; '+\
#                    self.se.entities[results[i][0]]['desc']+'; '\
#                    +self.se.entities[results[i][0]]['url'])

    def run(self):
        """
        Start server and respond to clients
        """
        # Create server socket using IPv4 addresses and TCP, allow reuse of socket.
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_address = ("0.0.0.0", self.port)
        server_socket.bind(server_address)
        server_socket.listen()
        while 1:
            print("Waiting for connection on port %d ..." % self.port, end="")
            sys.stdout.flush()
            connection, client_addr = server_socket.accept()
            connection.settimeout(5.0)
            print("Client from %s: %d" % client_addr)

            # Read request from client. Read in rounds untill a '\r\n\r\n' sequence.
            request = self.read_request(connection)

            # Default response.
            status_codes = {
                    200: "OK",
                    403: "Forbidden",
                    404: "Not found",
                    418: "I'm a teapot"
                    }
            media_types = {
                    "html": "text/html",
                    "css": "text/css",
                    "js": "application/javascript",
                    "gif": "image/gif",
                    "json": "application/json"
                    }
            response_bytes = b"Welcome!"
            status = 200
            content_type = "text/plain"
            requested_file = "search.html"

            # Compute results.
            if request[:3].lower() == "get":
                api, _, query = request.strip().split()[1][1:].strip().partition("?")
                if api:
                    requested_file = api
                try:
                    with open(requested_file, "rb") as fh:
                        response_bytes = fh.read()
                    content_type = media_types[requested_file.strip().rsplit('.', 1)[-1]]
                except FileNotFoundError:
                    status = 404
                    response_bytes = b"Requested file not found on server."
                except KeyError:
                    pass
                if requested_file == "search.html" and query:
                    search_results = self.answer_query(query[2:])
                    response_bytes = json.dumps(search_results).encode('utf-8')
                    content_type = media_types["json"]
#                    search_results = [f"{e['name']}; {e['desc']}; {e['url']}"\
#                            for e in self.answer_query(query[2:])]
#                    response_bytes = "<br>".join(search_results).encode()
#                    response_bytes = response_bytes\
#                            .replace(b"%QUERY%", query[2:].encode('utf-8'))\
#                            .replace(b"%RESULTS%", "<br>".join(search_results).encode('utf-8'))
            content_length = len(response_bytes)

            # Send response headers and content.
            headers = "HTTP/1.1 %d %s\r\n" \
                      "Content-Length: %d\r\n" \
                      "Content-Type: %s\r\n" \
                      "\r\n" % \
                      (status, status_codes[status], content_length, content_type)
            connection.sendall(headers.encode('utf-8'))
            connection.sendall(response_bytes)

            # Close the connection when the conversation finishes.
            connection.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 %s <file> <port> [-s/--use-synonyms]" % sys.argv[0])
        sys.exit(1)

    file = sys.argv[1]
    port = int(sys.argv[2])
    use_syn = False

    if len(sys.argv) == 4 and (sys.argv[3] == '--use-synonyms' or sys.argv[3] == '-s'):
        use_syn = True

    server = SearchServer(file, port)
    server.run()
