import os

class Song:
  id = ""
  songTitle = ""
  artist = ""
  album = ""
  duration = -1
  imgLoc = ""
  fileLoc = ""
  error = ""
  
  def __init__(self, id, songTitle, artist, album, duration, trackNum, imgLoc, fileLoc=""):
    self.id = id
    self.songTitle = songTitle.replace("|", '')
    self.artist = artist.replace("|", '')
    self.album = album.replace("|", '')
    self.duration = duration
    self.trackNum = trackNum
    self.imgLoc = imgLoc
    self.fileLoc = fileLoc
  
  @staticmethod
  def fromText(line):
    line = line.strip('\n')
    lineParts = line.split('|')
    
    if len(lineParts) != 8:
      return None
    
    id = lineParts[0]
    songTitle = lineParts[1]
    artist = lineParts[2]
    album = lineParts[3]
    duration = int(lineParts[4])
    trackNum = lineParts[5]
    imgLoc = lineParts[6]
    fileLoc = lineParts[7]
    
    return Song(id, songTitle, artist, album, duration, trackNum, imgLoc, fileLoc)
  
  @staticmethod
  def fromApiObj(apiObj):

    if apiObj['type'] == 'episode':
      return None

    id = apiObj['id'] \
      .replace('?', '') \
      .replace('/', '') \
      .replace('\\', '') \
      .replace('\'', '') \
      .replace('\"', '') \
      .replace('.', '')

    # get the song title, strip off any special chars
    songTitle = apiObj['name'] \
      .replace('?', '') \
      .replace('/', '') \
      .replace('\\', '') \
      .replace('\'', '') \
      .replace('\"', '') \
      .replace('.', '')

    # get the primary artist name, strip off any special chars
    artist = apiObj['artists'][0]['name'] \
      .replace('?', '') \
      .replace('/', '') \
      .replace('\\', '') \
      .replace('\'', '') \
      .replace('\"', '') \
      .replace('.', '')

    # get the album title, strip off any special chars
    album = apiObj['album']['name'] \
      .replace('?', '') \
      .replace('/', '') \
      .replace('\\', '') \
      .replace('\'', '') \
      .replace('\"', '') \
      .replace('.', '')

    trackNum = apiObj['track_number']

    # get the track duration as an integer
    duration = int(apiObj['duration_ms'])

    # get the cover art URL
    imgLoc = apiObj['album']['images'][0]['url']
    
    return Song(id, songTitle, artist, album, duration, trackNum, imgLoc)
  
  def toText(self):
    return f"{self.id}|{self.songTitle}|{self.artist}|{self.album}|{self.duration}|{self.trackNum}|{self.imgLoc}|{self.fileLoc}\n"
  
  def getM3uLine(self):
    return f"#EXTINF:{int(self.duration / 1000)},{self.artist} - {self.songTitle}\n" \
           f"{self.fileLoc}\n\n"
  
  def getSaveLoc(self, baseDir):
    artist = self.artist \
      .replace(':', '')
    
    album = self.album \
      .replace(':', '')
    
    title = self.songTitle \
      .replace(';', '')
    
    return os.path.join(baseDir, "tracks", artist, album, title)
  
  def tryFindMp3(self, outputDir):
    songFileLoc = self.getSaveLoc(outputDir) + ".mp3"
    
    if os.path.exists(songFileLoc):
      self.fileLoc = songFileLoc
      return True
    return False
