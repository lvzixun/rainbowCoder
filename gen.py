import time
import md
import os
import diff
import mgr
import json
import re
from datetime import datetime



class GeneratedRainbowCoder(object):
  post_dir = './post'
  # disqus = '''
  #   <div id="disqus_thread"></div>
  #   <script type="text/javascript">
  #     /* * * CONFIGURATION VARIABLES: EDIT BEFORE PASTING INTO YOUR WEBPAGE * * */
  #     var disqus_shortname = 'rainbowcoder'; // required: replace example with your forum shortname

  #     /* * * DON'T EDIT BELOW THIS LINE * * */
  #     (function() {
  #         var dsq = document.createElement('script'); dsq.type = 'text/javascript'; dsq.async = true;
  #         dsq.src = '//' + disqus_shortname + '.disqus.com/embed.js';
  #         (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(dsq);
  #     })();
  #   </script>
  #   <noscript>Please enable JavaScript to view the <a href="https://disqus.com/?ref_noscript">comments powered by Disqus.</a></noscript>
  # '''
  disqus = '''
    <script src="https://utteranc.es/client.js"
        repo="lvzixun/rainbowCoder"
        issue-term="pathname"
        theme="github-light"
        crossorigin="anonymous"
        async>
    </script>
  '''

  def __init__(self):
    self.cfg = mgr.cfg
    self.pattern = re.compile(r'"?(post/.*\.md)"?')
    self.idiff = diff.PostDiff()

  def _get_post(self, file_name):
    m = self.pattern.match(file_name)
    if m:
      name = m.groups()[0]
      return name.decode('string_escape')
    else:
      return False


  def _get_head_md(self):
    handle = open(self.cfg['head_md'], 'r')
    data = handle.read()
    handle.close()
    return data.decode('UTF-8')

  def _get_css(self):
    css = self.cfg['css']
    return '<link rel="stylesheet" type="text/css" href="%s">' % (css)

  def _get_filename(self, path):
    base = os.path.basename(path)
    return os.path.splitext(base)[0].decode('UTF-8')

  def _get_file(self, file):
    handle = open(file, 'r')
    data = handle.read()
    handle.close()
    return data.decode('UTF-8')

  def _save_file(self, file, str):
    handle = open(file, 'w')
    handle.write(str.encode('UTF-8'))
    handle.close()

  def _get_title(self, title):
    if title:
      return "<title>"+title+"</title>"
    return ""

  def _get_html_filename(self, md_file):
    title = self._get_filename(md_file)
    return "html/" + title + ".html"

  def _get_mdtitle(self, md_file):
    fd = open(md_file, "r")
    l = fd.readline()
    m = re.search(r"^\s*#+\s+(.+)$", l)
    t = unicode(m.group(1), "utf-8")
    fd.close()
    return t


  def get_html(self, md_file, title=None, suffix="", has_disqus=False):
    title = title or self._get_mdtitle(md_file)
    conv = md.MarkDownConvert(self._get_file(md_file) + suffix)

    html =  u'<!DOCTYPE html>'
    html += '<html><head><meta charset="utf-8">'
    html += self._get_css()
    html += self._get_title(title)
    html += "</head><body>"
    html += conv.md2html().decode('UTF-8')
    if has_disqus:
      html += self.disqus
    html += "</body>"
    html += "</html>"
    return html

  def _gen_post(self, md_file, title=None, suffix="", has_disqus=False):
    print "building: " + md_file
    html = self.get_html(md_file, title, suffix, has_disqus)
    html_file = self._get_html_filename(md_file)
    self._save_file(html_file, html)
    return html_file

  def get_post_list(self):
    ret = []
    list_post = os.listdir(self.post_dir)
    for line in list_post:
      md_file = os.path.join(self.post_dir, line)
      if os.path.isfile(md_file):
        filename = self._get_filename(md_file)
        if filename != 'index':
          last_time = self.idiff.diff_last_time(md_file)
          re_time = re.match(r"\s*(.*?)\s*\+", last_time).groups()[0]
          struct_time = time.strptime(re_time)
          ret.append({
              'title': self._get_mdtitle(md_file),
              'md_file': md_file,
              'html_file': filename + ".html",
              'create_date':  struct_time,
            })

    ret.sort(key=lambda item: item['create_date'], reverse = True)
    return ret

  def _format(self, title, html, date):
    # date = datetime.fromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')
    return '[%s](%s)\n' % (title, html)

  def building_index_md(self):
    post_list = self.get_post_list()
    head = self._get_head_md() + u'\n\n\n'
    for v in post_list:
      head += self._format(v['title'], v['html_file'], v['create_date'])
    
    index_md = self.cfg['index_md']
    self._save_file(index_md, head)
    self._gen_post(index_md, "rainbowCoder")


  def _wrapper_post(self, md_file):
    date = self.idiff.diff_last_time(md_file)
    date = "\n\n\n-----\n" + date
    self._gen_post(md_file, suffix=date, has_disqus=True)

  def building_all(self):
    post_list = self.get_post_list()
    self.building_index_md()
    for v in post_list:
      self._wrapper_post(v['md_file'])

  def building_post(self, md_file):
    self.building_index_md()
    self._wrapper_post(md_file)

  def building_update(self):
    diff_list = self.idiff.diff_list()

    for v in diff_list:
      file_name = self._get_post(v['file_name'])
      if file_name != False:
        self._wrapper_post(file_name)
        
    self.building_index_md()






