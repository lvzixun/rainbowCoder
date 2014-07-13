import sys
import gen
import mgr
import SocketServer


class TCPHandler(SocketServer.BaseRequestHandler):
  def __init__(self, request, client_address, server):
    self.rainbow = gen.GeneratedRainbowCoder()
    self.cmd_instruct = {
      "building_all": 
        lambda: self.rainbow.building_all(),
      "building_index": 
        lambda: self.rainbow.building_index_md(),
      "building_update": 
        lambda: self.rainbow.building_update(),
    }
    SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)

  def handle(self):
    cmd = self.request.recv(128).strip()
    ret = ""
    if not self.cmd_instruct.has_key(cmd):
      ret = "invalid instruct"
    else:
      try:
        self.cmd_instruct[cmd]()
        ret = "building success"
      except Exception, e:
        ret = "building fail:\n" + str(e)
    print("handle: " + cmd + "  send: " + ret)
    self.request.sendall(ret)

if __name__ == "__main__":
    HOST, PORT = "localhost", mgr.cfg['service_port']
    server = SocketServer.TCPServer((HOST, PORT), TCPHandler)
    server.serve_forever()

