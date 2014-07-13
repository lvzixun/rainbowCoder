import sys
import gen

rainbow = gen.GeneratedRainbowCoder()


cmd_instruct = {
  "building_all": 
    lambda: rainbow.building_all(),
  "building_index": 
    lambda: rainbow.building_index_md(),
  "building_update": 
    lambda: rainbow.building_update(),
}

def use_page():
  cmd = ""
  for (k, v) in cmd_instruct.items():
    cmd += "    " + k + "\n"

  print('use_page: \n python cmd.py <cmd>\n cmd list:\n' + cmd)
  exit()


def run(cmd):
  func = cmd_instruct[cmd]
  if not func:
    use_page()
  else:
    func()


argv = sys.argv

if len(argv) != 2:
  use_page()

run(argv[1])