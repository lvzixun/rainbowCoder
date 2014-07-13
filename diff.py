from git import *

class PostDiff(object):
  git_path = ".git"
  
  def __init__(self):
    self.repo = Repo(self.git_path)
    self.origin = self.repo.remotes.origin

  def _cur_local_hexsha(self):
    hcommit = self.repo.head.commit
    return hcommit.hexsha

  def _remote_idiff(self):
    local_hexsha = self._cur_local_hexsha()
    self.origin.pull()
    hcommit = self.repo.head.commit
    return hcommit.diff(local_hexsha)

  def _diff_(self, idiff, change_type):
    ret = []
    for v in idiff.iter_change_type(change_type):
      file_name = None
      if v.a_blob:
        file_name = v.a_blob.path
      elif v.b_blob:
        file_name = v.b_blob.path
      else:
        assert(False)

      ret.append({
          "file_name": file_name,
          "change_type": change_type
        })
    return ret

  def diff_list(self):
    ret = []
    idiff = self._remote_idiff()

    print(idiff)
    ret.extend(self._diff_(idiff, 'A')) # insert add file
    ret.extend(self._diff_(idiff, 'M')) # insert modify file
    return ret

    
