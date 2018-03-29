import urllib
import json
import markdown2

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
    s = self.data["text"]
    html = markdown2.markdown(s)
    return html.encode("utf-8")
    # params = json.dumps(self.data).encode("utf-8")
    # handle = urllib.urlopen("https://api.github.com/markdown", params)
    # return handle.read()