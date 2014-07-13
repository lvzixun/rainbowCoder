import urllib
import json

class MarkDownConvert(object):
  headers = {
    'Content-Type': 'application/json'
  }

  def __init__(self, md):
    self.data = {
      "text": md,
      "mode": "gfm"
    }

  def md2html(self):
    params = json.dumps(self.data).encode("utf-8")
    handle = urllib.urlopen("https://api.github.com/markdown", params)
    return handle.read()