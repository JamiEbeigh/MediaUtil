import os
import shutil
import ffmpeg
import subprocess
from util.UtilOptions import UtilOptions

class MkvConverter:
  _options = None
  
  def __init__(self, options):
    self._options = options
    
  def runConvert(self):
    toConvertDir = os.path.join(self._options.moviesDir, 'toConvert')
    subDirs = []
    
    for f in os.listdir(toConvertDir):
      d = os.path.join(toConvertDir, f)
      if os.path.isdir( d ):
        subDirs.append(d)
    
    for d in subDirs:
      dataFileLoc = os.path.join(d, 'data.txt')
      title, year = self.parseDataFile(dataFileLoc)
      
      if title == '':
        continue
        
      targetDir = os.path.join(self._options.moviesDir, f'{title} ({year})')
      mkv, srt = self.findFiles(d)
      
      if os.path.exists(targetDir):
        shutil.rmtree(targetDir)
      
      os.mkdir(targetDir)
      
      if srt != '':
        tartgetSrt = os.path.join(targetDir, f'{title}.srt')
        shutil.copy(srt, tartgetSrt)

      targetMkv = os.path.join(targetDir, f'{title}.mov')

      try:
        subprocess.run(
          ["ffmpeg", "-i", mkv, "-codec", "copy", targetMkv], check=True
        )
      except:
        raise Exception(
          "Please DOWNLOAD, INSTALL & ADD the path of FFMPEG to Environment Variables!"
        )

  def convert_to_mp4(self, mkvFile):
    name, ext = os.path.splitext(mkvFile)
    out_name = name + ".mp4"
    ffmpeg.input(mkvFile).output(out_name).run()
    print("Finished converting {}".format(mkvFile))
    
  def parseDataFile(self, dataFileLoc):
    if not os.path.exists( dataFileLoc ):
      return "", ""
    
    title = ""
    year = ""
    
    for l in open( dataFileLoc, 'r' ).readlines():
      p = l.split('=')
      
      if len(p) != 2:
        continue
      
      key = p[0].strip()
      val = p[1].strip('\'"\n')
      
      if key == 'title':
        title = val
      if key == 'year':
        year = val
        
    return title, year
  
  def findFiles(self, dir):
    mkv = ""
    srt = ""
    
    for f in os.listdir(dir):
      if f.startswith('.'):
        continue
        
      if f.endswith('.mkv'):
        mkv = os.path.join(dir, f)
      if f.endswith('.srt'):
        srt = os.path.join(dir, f)
    
    return mkv, srt
    
    
def __main__():
  o = UtilOptions("../dataFiles/options.txt")
  c = MkvConverter(o)
  c.runConvert()

if __name__ == "__main__":
  __main__()