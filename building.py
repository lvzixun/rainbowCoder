import sys
import gen
import mgr
import os


argv = sys.argv

class Building(object):
  def __init__(self):
    self.rainbow = gen.GeneratedRainbowCoder()
    self.cmd_instruct = {
      "building_all": 
        lambda: self.rainbow.building_all(),
      "building_index": 
        lambda: self.rainbow.building_index_md(),
      "building_update": 
        lambda: self.rainbow.building_update(),
      "building_post":
        lambda: self.rainbow.building_post(argv[2]),
      "building_rss":
        lambda: os.system("lua rss.lua"),
    }

  def use_page(self):
    cmd = ""
    for (k, v) in self.cmd_instruct.items():
      cmd += "    " + k + "\n"
    print('use_page: \n python cmd.py <cmd>\n cmd list:\n' + cmd)
    exit()

  def run(self, cmd):
    if not self.cmd_instruct.has_key(cmd):
      self.use_page()
    else:
      func = self.cmd_instruct[cmd]
      func()


building = Building()

if len(argv) < 2:
  building.use_page()

building.run(argv[1])