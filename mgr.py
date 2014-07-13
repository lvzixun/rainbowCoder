import json

def _gen_cfg():
  handle = open('cfg.json', 'r')
  cfg = json.loads(handle.read())
  handle.close()
  return cfg

cfg = _gen_cfg()