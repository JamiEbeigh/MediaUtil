import os
import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, TRCK, USLT
import lyricsgenius
from util.decorators import background

class Song:
  id = ""
  songTitle = ""
  artist = ""
  album = ""
  duration = -1
  trackNum = -1
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
  
  def tryFindLyrics(self):
    if self.fileLoc == '' or not os.path.exists( self.fileLoc ):
      return False
    
    c = ID3(self.fileLoc)
    if 'USLT::eng' in c and c["USLT::eng"].text != '':
      return True
    return False
  def setFileMeta(self):
    '''
    Set the ID3 and APIC data for an mp3 file to the values pulled from spotify

    PARAMETERS:
      fileLoc - the mp3 file to be modified
      title - song title
      artist - song artist
      album - album title
      coverUrl - link to the album cover (retrieved from spotify)
    '''
  
    # set the ID3 data using mutigen
    c = EasyID3(self.fileLoc)
    c.clear()  # clear all current tags before assigning new ones
    c['title'] = self.songTitle
    c['artist'] = self.artist
    c['album'] = self.album
    c['albumartist'] = self.artist
    c.save()
  
    # send a get request to retrieve the cover art
    cover_data = requests.get(self.imgLoc).content
  
    # embed the cover art in the file
    c = ID3(self.fileLoc)
    c['APIC'] = APIC(
      encoding=3,
      mime='image/jpeg',
      type=3, desc=u'Cover',
      data=cover_data
    )
    c['TRCK'] = TRCK(encoding=3, text=str(self.trackNum))
  
    c.save()
  
  def getLyrics(self):
    geniusToken = "bIOQmT0Ob0U8LTZhz1nYTJOESxQssNa5XiI3mkwThlyJvtzT1xWv8U1ibNR8jQei"
    if not os.path.exists(self.fileLoc):
      return
    
    g = lyricsgenius.Genius( geniusToken )
    
    try:
      results = g.search( f'{self.songTitle} {self.artist}' )
    except:
      return
    
    if not 'hits' in results \
        or len(results['hits']) == 0 or \
        not 'result' in results['hits'][0]:
      return
    
    songLink = results['hits'][0]['result']['url']
    
    try:
      lyrics = g.lyrics(song_url=songLink, remove_section_headers=True)
    except:
      return
    
    if lyrics == '':
      return
    
    lyrics = lyrics[lyrics.find("Lyrics")+6:]
    
    c = ID3(self.fileLoc)
    c['USLT'] = USLT(encoding=3, text=lyrics, lang='eng')
    c.save()